import bpy
import math
import sys

################################################################################
# Scene
################################################################################


def set_animation(scene, fps=24, frame_start=1, frame_end=48, frame_current=1):
    scene.render.fps = fps
    scene.frame_start = frame_start
    scene.frame_end = frame_end
    scene.frame_current = frame_current


def build_rgb_background(world, rgb=(0.9, 0.9, 0.9, 1.0), strength=1.0):
    world.use_nodes = True
    node_tree = world.node_tree

    rgb_node = node_tree.nodes.new(type="ShaderNodeRGB")
    rgb_node.outputs["Color"].default_value = rgb

    node_tree.nodes["Background"].inputs["Strength"].default_value = strength

    node_tree.links.new(rgb_node.outputs["Color"], node_tree.nodes["Background"].inputs["Color"])

    arrange_nodes(node_tree)


def build_environment_texture_background(world, hdri_path, rotation=0.0):
    world.use_nodes = True
    node_tree = world.node_tree

    environment_texture_node = node_tree.nodes.new(type="ShaderNodeTexEnvironment")
    environment_texture_node.image = bpy.data.images.load(hdri_path)

    mapping_node = node_tree.nodes.new(type="ShaderNodeMapping")
    mapping_node.rotation[2] = rotation

    tex_coord_node = node_tree.nodes.new(type="ShaderNodeTexCoord")

    node_tree.links.new(tex_coord_node.outputs["Generated"], mapping_node.inputs["Vector"])
    node_tree.links.new(mapping_node.outputs["Vector"], environment_texture_node.inputs["Vector"])
    node_tree.links.new(environment_texture_node.outputs["Color"], node_tree.nodes["Background"].inputs["Color"])

    arrange_nodes(node_tree)


def set_cycles_renderer(scene,
                        resolution_percentage,
                        output_file_path,
                        camera,
                        num_samples,
                        use_denoising=True,
                        use_motion_blur=False,
                        use_transparent_bg=False):
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_percentage = resolution_percentage
    scene.render.engine = 'CYCLES'
    scene.render.filepath = output_file_path
    scene.render.use_freestyle = False
    scene.cycles.samples = num_samples
    scene.render.layers[0].cycles.use_denoising = use_denoising
    scene.camera = camera
    scene.render.use_motion_blur = use_motion_blur
    scene.cycles.film_transparent = use_transparent_bg


def set_camera_params(camera, focus_target):
    # Simulate Sony's FE 85mm F1.4 GM
    camera.data.sensor_fit = 'HORIZONTAL'
    camera.data.sensor_width = 36.0
    camera.data.sensor_height = 24.0
    camera.data.lens = 85
    camera.data.dof_object = focus_target
    camera.data.cycles.aperture_type = 'FSTOP'
    camera.data.cycles.aperture_fstop = 1.4
    camera.data.cycles.aperture_blades = 11


################################################################################
# Modifiers
################################################################################


def add_subdivision_surface_modifier(mesh, level, is_simple=False):
    modifier = mesh.modifiers.new(name="Subsurf", type='SUBSURF')
    modifier.levels = level
    modifier.render_levels = level
    modifier.subdivision_type = 'SIMPLE' if is_simple else 'CATMULL_CLARK'


################################################################################
# Constraints
################################################################################


def add_track_to_constraint(camera, track_to_target):
    constraint = camera.constraints.new(type='TRACK_TO')
    constraint.target = track_to_target
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'


def add_copy_location_constraint(copy_to_object, copy_from_object, use_x, use_y, use_z, bone_name=''):
    constraint = copy_to_object.constraints.new(type='COPY_LOCATION')
    constraint.target = copy_from_object
    constraint.use_x = use_x
    constraint.use_y = use_y
    constraint.use_z = use_z
    if bone_name:
        constraint.subtarget = bone_name


################################################################################
# Shading
################################################################################


def create_texture_node(node_tree, path, is_color_data):
    # Instantiate a new texture image node
    texture_node = node_tree.nodes.new(type='ShaderNodeTexImage')

    # Open an image and set it to the node
    texture_node.image = bpy.data.images.load(path)

    # Set other parameters
    texture_node.color_space = 'COLOR' if is_color_data else 'NONE'

    # Return the node
    return texture_node


def set_principled_node(principled_node,
                        base_color=(0.6, 0.6, 0.6, 1.0),
                        subsurface=0.0,
                        subsurface_color=(0.8, 0.8, 0.8, 1.0),
                        subsurface_radius=(1.0, 0.2, 0.1),
                        metallic=0.0,
                        specular=0.5,
                        specular_tint=0.0,
                        roughness=0.5,
                        anisotropic=0.0,
                        anisotropic_rotation=0.0,
                        sheen=0.0,
                        sheen_tint=0.5,
                        clearcoat=0.0,
                        clearcoat_roughness=0.03,
                        ior=1.45,
                        transmission=0.0,
                        transmission_roughness=0.0):
    principled_node.inputs['Base Color'].default_value = base_color
    principled_node.inputs['Subsurface'].default_value = subsurface
    principled_node.inputs['Subsurface Color'].default_value = subsurface_color
    principled_node.inputs['Subsurface Radius'].default_value = subsurface_radius
    principled_node.inputs['Metallic'].default_value = metallic
    principled_node.inputs['Specular'].default_value = specular
    principled_node.inputs['Specular Tint'].default_value = specular_tint
    principled_node.inputs['Roughness'].default_value = roughness
    principled_node.inputs['Anisotropic'].default_value = anisotropic
    principled_node.inputs['Anisotropic Rotation'].default_value = anisotropic_rotation
    principled_node.inputs['Sheen'].default_value = sheen
    principled_node.inputs['Sheen Tint'].default_value = sheen_tint
    principled_node.inputs['Clearcoat'].default_value = clearcoat
    principled_node.inputs['Clearcoat Roughness'].default_value = clearcoat_roughness
    principled_node.inputs['IOR'].default_value = ior
    principled_node.inputs['Transmission'].default_value = transmission
    principled_node.inputs['Transmission Roughness'].default_value = transmission_roughness


def build_pbr_nodes(node_tree, base_color=(0.6, 0.6, 0.6, 1.0), metallic=0.0, specular=0.5, roughness=0.5, sheen=0.0):
    output_node = node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    principled_node = node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    node_tree.links.new(principled_node.outputs['BSDF'], output_node.inputs['Surface'])

    set_principled_node(principled_node=principled_node,
                        base_color=base_color,
                        metallic=metallic,
                        specular=specular,
                        roughness=roughness,
                        sheen=sheen)

    arrange_nodes(node_tree)


def build_matcap_nodes(node_tree, image_path):
    tex_coord_node = node_tree.nodes.new(type='ShaderNodeTexCoord')
    vector_transform_node = node_tree.nodes.new(type='ShaderNodeVectorTransform')
    mapping_node = node_tree.nodes.new(type='ShaderNodeMapping')
    texture_image_node = create_texture_node(node_tree, image_path, True)
    emmission_node = node_tree.nodes.new(type='ShaderNodeEmission')
    output_node = node_tree.nodes.new(type='ShaderNodeOutputMaterial')

    frame = node_tree.nodes.new(type='NodeFrame')
    frame.name = "MatCap UV"
    frame.label = "MatCap UV"
    tex_coord_node.parent = frame
    vector_transform_node.parent = frame
    mapping_node.parent = frame

    vector_transform_node.vector_type = "VECTOR"
    vector_transform_node.convert_from = "OBJECT"
    vector_transform_node.convert_to = "CAMERA"

    mapping_node.vector_type = "TEXTURE"
    mapping_node.translation = (1.0, 1.0, 0.0)
    mapping_node.scale = (2.0, 2.0, 1.0)

    node_tree.links.new(tex_coord_node.outputs['Normal'], vector_transform_node.inputs['Vector'])
    node_tree.links.new(vector_transform_node.outputs['Vector'], mapping_node.inputs['Vector'])
    node_tree.links.new(mapping_node.outputs['Vector'], texture_image_node.inputs['Vector'])
    node_tree.links.new(texture_image_node.outputs['Color'], emmission_node.inputs['Color'])
    node_tree.links.new(emmission_node.outputs['Emission'], output_node.inputs['Surface'])

    arrange_nodes(node_tree)


def build_pbr_textured_nodes(node_tree,
                             color_texture_path="",
                             metallic_texture_path="",
                             roughness_texture_path="",
                             normal_texture_path="",
                             displacement_texture_path="",
                             ambient_occlusion_texture_path="",
                             scale=(1.0, 1.0, 1.0)):
    output_node = node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    principled_node = node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    node_tree.links.new(principled_node.outputs['BSDF'], output_node.inputs['Surface'])

    coord_node = node_tree.nodes.new(type='ShaderNodeTexCoord')
    mapping_node = node_tree.nodes.new(type='ShaderNodeMapping')
    mapping_node.vector_type = 'TEXTURE'
    mapping_node.scale = scale
    node_tree.links.new(coord_node.outputs['UV'], mapping_node.inputs['Vector'])

    if color_texture_path != "":
        texture_node = create_texture_node(node_tree, color_texture_path, True)
        node_tree.links.new(mapping_node.outputs['Vector'], texture_node.inputs['Vector'])
        if ambient_occlusion_texture_path != "":
            ao_texture_node = create_texture_node(node_tree, ambient_occlusion_texture_path, False)
            node_tree.links.new(mapping_node.outputs['Vector'], ao_texture_node.inputs['Vector'])
            mix_node = node_tree.nodes.new(type='ShaderNodeMixRGB')
            mix_node.blend_type = 'MULTIPLY'
            node_tree.links.new(texture_node.outputs['Color'], mix_node.inputs['Color1'])
            node_tree.links.new(ao_texture_node.outputs['Color'], mix_node.inputs['Color2'])
            node_tree.links.new(mix_node.outputs['Color'], principled_node.inputs['Base Color'])
        else:
            node_tree.links.new(texture_node.outputs['Color'], principled_node.inputs['Base Color'])

    if metallic_texture_path != "":
        texture_node = create_texture_node(node_tree, metallic_texture_path, False)
        node_tree.links.new(mapping_node.outputs['Vector'], texture_node.inputs['Vector'])
        node_tree.links.new(texture_node.outputs['Color'], principled_node.inputs['Metallic'])

    if roughness_texture_path != "":
        texture_node = create_texture_node(node_tree, roughness_texture_path, False)
        node_tree.links.new(mapping_node.outputs['Vector'], texture_node.inputs['Vector'])
        node_tree.links.new(texture_node.outputs['Color'], principled_node.inputs['Roughness'])

    if normal_texture_path != "":
        texture_node = create_texture_node(node_tree, normal_texture_path, False)
        node_tree.links.new(mapping_node.outputs['Vector'], texture_node.inputs['Vector'])
        normal_map_node = node_tree.nodes.new(type='ShaderNodeNormalMap')
        node_tree.links.new(texture_node.outputs['Color'], normal_map_node.inputs['Color'])
        node_tree.links.new(normal_map_node.outputs['Normal'], principled_node.inputs['Normal'])

    if displacement_texture_path != "":
        texture_node = create_texture_node(node_tree, displacement_texture_path, False)
        node_tree.links.new(mapping_node.outputs['Vector'], texture_node.inputs['Vector'])
        node_tree.links.new(texture_node.outputs['Color'], output_node.inputs['Displacement'])

    arrange_nodes(node_tree)


################################################################################
# Misc.
################################################################################


def clean_objects():
    for item in bpy.data.objects:
        bpy.data.objects.remove(item)


def clean_nodes(nodes):
    for node in nodes:
        nodes.remove(node)


def arrange_nodes(node_tree, verbose=False):
    max_num_iters = 2000
    epsilon = 1e-05
    target_space = 50.0

    second_stage = False

    fix_horizontal_location = True
    fix_vertical_location = True
    fix_overlaps = True

    if verbose:
        print("-----------------")
        print("Target nodes:")
        for node in node_tree.nodes:
            print("- " + node.name)

    # In the first stage, expand nodes overly
    target_space *= 2.0

    # Gauss-Seidel-style iterations
    previous_squared_deltas_sum = sys.float_info.max
    for i in range(max_num_iters):
        squared_deltas_sum = 0.0

        if fix_horizontal_location:
            for link in node_tree.links:
                k = 0.9 if not second_stage else 0.5
                threshold_factor = 2.0

                x_from = link.from_node.location[0]
                x_to = link.to_node.location[0]
                w_from = link.from_node.width
                signed_space = x_to - x_from - w_from
                C = signed_space - target_space
                grad_C_x_from = -1.0
                grad_C_x_to = 1.0

                # Skip if the distance is sufficiently large
                if C >= target_space * threshold_factor:
                    continue

                lagrange = C / (grad_C_x_from * grad_C_x_from + grad_C_x_to * grad_C_x_to)
                delta_x_from = -lagrange * grad_C_x_from
                delta_x_to = -lagrange * grad_C_x_to

                link.from_node.location[0] += k * delta_x_from
                link.to_node.location[0] += k * delta_x_to

                squared_deltas_sum += k * k * (delta_x_from * delta_x_from + delta_x_to * delta_x_to)

        if fix_vertical_location:
            k = 0.5 if not second_stage else 0.05
            socket_offset = 20.0

            def get_from_socket_index(node, node_socket):
                for i in range(len(node.outputs)):
                    if node.outputs[i] == node_socket:
                        return i
                assert False

            def get_to_socket_index(node, node_socket):
                for i in range(len(node.inputs)):
                    if node.inputs[i] == node_socket:
                        return i
                assert False

            for link in node_tree.links:
                from_socket_index = get_from_socket_index(link.from_node, link.from_socket)
                to_socket_index = get_to_socket_index(link.to_node, link.to_socket)
                y_from = link.from_node.location[1] - socket_offset * from_socket_index
                y_to = link.to_node.location[1] - socket_offset * to_socket_index
                C = y_from - y_to
                grad_C_y_from = 1.0
                grad_C_y_to = -1.0
                lagrange = C / (grad_C_y_from * grad_C_y_from + grad_C_y_to * grad_C_y_to)
                delta_y_from = -lagrange * grad_C_y_from
                delta_y_to = -lagrange * grad_C_y_to

                link.from_node.location[1] += k * delta_y_from
                link.to_node.location[1] += k * delta_y_to

                squared_deltas_sum += k * k * (delta_y_from * delta_y_from + delta_y_to * delta_y_to)

        if fix_overlaps and second_stage:
            k = 0.9
            margin = 0.5 * target_space

            # Examine all node pairs
            for node_1 in node_tree.nodes:
                for node_2 in node_tree.nodes:
                    if node_1 == node_2:
                        continue

                    x_1 = node_1.location[0]
                    x_2 = node_2.location[0]
                    w_1 = node_1.width
                    w_2 = node_2.width
                    cx_1 = x_1 + 0.5 * w_1
                    cx_2 = x_2 + 0.5 * w_2
                    rx_1 = 0.5 * w_1 + margin
                    rx_2 = 0.5 * w_2 + margin

                    # Note: "dimensions" and "height" may not be correct depending on the situation
                    def get_height(node):
                        if node.dimensions.y > epsilon:
                            return node.dimensions.y
                        elif math.fabs(node.height - 100.0) > epsilon:
                            return node.height
                        else:
                            return 200.0

                    y_1 = node_1.location[1]
                    y_2 = node_2.location[1]
                    h_1 = get_height(node_1)
                    h_2 = get_height(node_2)
                    cy_1 = y_1 - 0.5 * h_1
                    cy_2 = y_2 - 0.5 * h_2
                    ry_1 = 0.5 * h_1 + margin
                    ry_2 = 0.5 * h_2 + margin

                    C_x = math.fabs(cx_1 - cx_2) - (rx_1 + rx_2)
                    C_y = math.fabs(cy_1 - cy_2) - (ry_1 + ry_2)

                    # If no collision, just skip
                    if C_x >= 0.0 or C_y >= 0.0:
                        continue

                    # Solve collision for the "easier" direction
                    if C_x > C_y:
                        grad_C_x_1 = 1.0 if cx_1 - cx_2 >= 0.0 else -1.0
                        grad_C_x_2 = -1.0 if cx_1 - cx_2 >= 0.0 else 1.0
                        lagrange = C_x / (grad_C_x_1 * grad_C_x_1 + grad_C_x_2 * grad_C_x_2)
                        delta_x_1 = -lagrange * grad_C_x_1
                        delta_x_2 = -lagrange * grad_C_x_2

                        node_1.location[0] += k * delta_x_1
                        node_2.location[0] += k * delta_x_2

                        squared_deltas_sum += k * k * (delta_x_1 * delta_x_1 + delta_x_2 * delta_x_2)
                    else:
                        grad_C_y_1 = 1.0 if cy_1 - cy_2 >= 0.0 else -1.0
                        grad_C_y_2 = -1.0 if cy_1 - cy_2 >= 0.0 else 1.0
                        lagrange = C_y / (grad_C_y_1 * grad_C_y_1 + grad_C_y_2 * grad_C_y_2)
                        delta_y_1 = -lagrange * grad_C_y_1
                        delta_y_2 = -lagrange * grad_C_y_2

                        node_1.location[1] += k * delta_y_1
                        node_2.location[1] += k * delta_y_2

                        squared_deltas_sum += k * k * (delta_y_1 * delta_y_1 + delta_y_2 * delta_y_2)

        if verbose:
            print("Iteration #" + str(i) + ": " + str(previous_squared_deltas_sum - squared_deltas_sum))

        # Check the termination conditiion
        if math.fabs(previous_squared_deltas_sum - squared_deltas_sum) < epsilon:
            if second_stage:
                break
            else:
                target_space = 0.5 * target_space
                second_stage = True

        previous_squared_deltas_sum = squared_deltas_sum
