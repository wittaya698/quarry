extends SceneTree

var scenes = {}

func _initialize():
	for scene_name in ["meadow", "long_climb"]:
		scenes[scene_name] = load("res://%s.tscn" % scene_name).instantiate()
		root.add_child(scenes[scene_name])

func _process(_delta):
	for scene_name in scenes:
		print("=== ", scene_name, ".tscn")
		_dump(scenes[scene_name], 0)
	return true

func _dump(node, depth):
	var line = "  ".repeat(depth) + "%s [%s]" % [node.name, node.get_class()]
	if node is Node3D:
		line += " global=%s" % [node.global_position]
	if node is MeshInstance3D and node.mesh:
		var m = node.mesh
		line += " surfaces=%d prim=%d verts=%d" % [m.get_surface_count(), m.surface_get_primitive_type(0), m.surface_get_array_len(0)]
	if node is CollisionShape3D and node.shape:
		line += " shape=%s" % node.shape.get_class()
		if node.shape is ConcavePolygonShape3D:
			line += " faces=%d" % (node.shape.get_faces().size() / 3)
	for key in node.get_meta_list():
		var value = node.get_meta(key)
		line += " meta[%s]=%s" % [key, (str(value).substr(0, 90))]
	print(line)
	for child in node.get_children():
		_dump(child, depth + 1)
