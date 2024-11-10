import re
from flask import g

POINTER_REGEX = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\*+$')
ARRAY_REGEX = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]* \[(\d+)\]$')

POINTER_DATA_REGEX = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*\.\*[a-zA-Z_][a-zA-Z0-9_]*$')
CLASS_MEMBERS_REGEX = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)?\.(public|private|protected)\.[a-zA-Z_][a-zA-Z0-9_]*$')

def get_trace_step(gdb_controller, gdb_command):
    step = {'function': '', 'line': -1, 'stack_frames': [], 'heap': {}, 'stdout': ''}

    results = gdb_controller.write(gdb_command)
    if results[-1]['payload'].get('frame') and results[-1]['payload']['frame']['func'] == '__libc_start_call_main':
        return 'main_returned'
    
    stdout = next((res['payload'] for res in results if res['type'] == 'output'), '')
    
    heap = {}
    stack_frames = []
    update_program_state(gdb_controller=gdb_controller, stack_frames=stack_frames, heap=heap)

    step.update({'function': results[-1]['payload']['frame']['func'],
                 'line': results[-1]['payload']['frame']['line'],
                 'stack_frames': stack_frames,
                 'heap': heap,
                 'stdout': stdout})
    return step

def update_program_state(gdb_controller, stack_frames, heap):
    results = gdb_controller.write('-stack-list-frames')
    stack = results[0]['payload']['stack']

    for frame in stack:
        stack_frame = {'function': frame['func'], 'local_variables': []}
        frame_level = frame['level']

        gdb_controller.write(f'-stack-select-frame {frame_level}')
        results = gdb_controller.write('-stack-list-variables --simple-values')

        local_variables = []
        local_vars = results[0]['payload']['variables']

        for var in local_vars:
            if not g.variables_dict.get(var['name']):
                result = gdb_controller.write(f"-var-create {var['name']} * {var['name']}")
                g.variables_dict.update({var['name']: result[0]['payload']})

            if POINTER_REGEX.match(var['type']):
                pointer_type = get_pointer_type(gdb_controller=gdb_controller, pointer_varobj=g.variables_dict.get(var['name']), heap=heap)
                local_variables.append(pointer_type)
            elif ARRAY_REGEX.match(var['type']):
                array_var = get_array_type(gdb_controller=gdb_controller, array_varobj=var)
                local_variables.append(array_var)
            else:
                primitive_var = get_primitive_type(gdb_controller=gdb_controller, primitive_varobj=var)
                local_variables.append(primitive_var)
        
        stack_frame.update({'local_variables': local_variables})
        stack_frames.append(stack_frame)

def get_primitive_type(gdb_controller, primitive_varobj):
    var_name = primitive_varobj['name']
    var_dtype = primitive_varobj['type']
    results = gdb_controller.write(f'-data-evaluate-expression &{var_name}')
    var_address = results[0]['payload']['value']

    gdb_controller.write(f'-var-update --all-values {var_name}')

    var_value = []
    populate_varobj_children(gdb_controller=gdb_controller, var_obj_name=var_name, children=var_value)

    if len(var_value) == 0:
        var_value = primitive_varobj['value']

    return {'address': var_address.split(' ')[0], 
            'name': var_name, 
            'data_type': var_dtype, 
            'value': var_value}

def get_array_type(gdb_controller, array_varobj):
    var_name = array_varobj['name']
    var_dtype = array_varobj['type']
    results = gdb_controller.write(f'-data-evaluate-expression &{var_name}')
    var_address = results[0]['payload']['value']

    gdb_controller.write(f'-var-update --all-values {var_name}')

    results = gdb_controller.write(f'-var-list-children --all-values {var_name}')
    child_items = results[0]['payload']['children']
    var_value = [item['value'] for item in child_items]

    return {'address': var_address.split(' ')[0], 
            'name': var_name, 
            'data_type': var_dtype, 
            'value': chr(int(var_value)) if var_dtype == 'char' else var_value}

def get_pointer_type(gdb_controller, pointer_varobj, heap):
    var_name = pointer_varobj['name']  
    var_dtype = pointer_varobj['type']
    results = gdb_controller.write(f'-data-evaluate-expression &{var_name}')
    var_address = results[0]['payload']['value']

    gdb_controller.write(f'-var-update --all-values {var_name}')

    result = gdb_controller.write(f'-var-evaluate-expression {var_name}')
    var_value = result[0]['payload']['value'].split(' ')[0]

    heap_dtype = pointer_varobj['type'].split(' ')[0]
    heap_value = []
    populate_varobj_children(gdb_controller=gdb_controller, var_obj_name=var_name, children=heap_value)

    heap.update({var_value: [heap_dtype, heap_value]})

    return {'address': var_address.split(' ')[0], 
            'name': var_name, 
            'data_type': var_dtype, 
            'value': var_value.split(' ')[0]}

def populate_varobj_children(gdb_controller, var_obj_name, children):
    result = gdb_controller.write(f'-var-list-children --all-values {var_obj_name}')
    children_count = int(result[0]['payload']['numchild'])

    if children_count == 0:
        return
    
    child_list = result[0]['payload']['children']
    for child in child_list:
        if CLASS_MEMBERS_REGEX.match(child['name']):
            if ARRAY_REGEX.match(child['type']):
                results = gdb_controller.write(f"-var-list-children --simple-values {child['name']}")
                child_items = results[0]['payload']['children']
                values = [item['value'] for item in child_items]
                children.append([child['name'], child['type'], child['exp'], values])
                continue
            children.append([child['name'], child['type'], child['exp'], child['value']])
            populate_varobj_children(gdb_controller, child['name'], children)
        elif POINTER_DATA_REGEX.match(child['name']):
            children.extend([child['name'], child['exp'], child['value']])
            continue
        else:
            populate_varobj_children(gdb_controller, child['name'], children)
