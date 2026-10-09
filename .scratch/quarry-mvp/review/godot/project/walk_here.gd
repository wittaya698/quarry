extends Node3D
## Walk an exported Quarry Site first-person.
## Change `site` to the name of any exported .tscn beside this file.

@export var site := "long_climb"
@export var walk_speed := 1.4  # the Brief's Walk Speed, m/s

const SPRINT := 5.0  # times faster while Shift is held; the timer says when you used it
const LOOK := 0.003

var player: CharacterBody3D
var head: Node3D
var hud: Label
var landmarks := []  # Node3D anchors
var timer := 0.0
var timing := false
var sprinted := false
var from := ""

func _ready():
	var scene = load("res://%s.tscn" % site).instantiate()
	add_child(scene)
	landmarks = scene.find_child("landmarks", true, false).get_children()
	for anchor in landmarks:
		_pole(anchor.global_position)

	var sun = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, -30, 0)
	sun.shadow_enabled = true
	add_child(sun)
	var environment = WorldEnvironment.new()
	environment.environment = Environment.new()
	environment.environment.background_mode = Environment.BG_SKY
	environment.environment.sky = Sky.new()
	environment.environment.sky.sky_material = ProceduralSkyMaterial.new()
	environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	add_child(environment)

	player = CharacterBody3D.new()
	var shape = CollisionShape3D.new()
	shape.shape = CapsuleShape3D.new()
	shape.shape.radius = 0.4
	shape.shape.height = 1.8
	player.add_child(shape)
	head = Node3D.new()
	head.position.y = 0.7
	player.add_child(head)
	var camera = Camera3D.new()
	camera.far = 2000
	head.add_child(camera)
	add_child(player)
	_go_to(0)

	hud = Label.new()
	hud.position = Vector2(16, 16)
	hud.add_theme_font_size_override("font_size", 18)
	hud.add_theme_color_override("font_outline_color", Color.BLACK)
	hud.add_theme_constant_override("outline_size", 6)
	add_child(hud)
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _pole(at: Vector3):
	var pole = MeshInstance3D.new()
	pole.mesh = CylinderMesh.new()
	pole.mesh.top_radius = 0.3
	pole.mesh.bottom_radius = 0.3
	pole.mesh.height = 6.0
	var material = StandardMaterial3D.new()
	material.albedo_color = Color(1.0, 0.45, 0.1)
	material.emission_enabled = true
	material.emission = Color(1.0, 0.45, 0.1)
	pole.mesh.material = material
	pole.position = at + Vector3.UP * 3.0
	add_child(pole)

func _go_to(index: int):
	if index >= landmarks.size():
		return
	var anchor: Node3D = landmarks[index]
	player.global_position = anchor.global_position + Vector3.UP * 1.0
	player.velocity = Vector3.ZERO
	timer = 0.0
	timing = false
	sprinted = false
	from = anchor.name

func _unhandled_input(event):
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		player.rotate_y(-event.relative.x * LOOK)
		head.rotate_x(-event.relative.y * LOOK)
		head.rotation.x = clamp(head.rotation.x, -1.5, 1.5)
	elif event is InputEventMouseButton and event.pressed:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif event is InputEventKey and event.pressed:
		if event.keycode == KEY_ESCAPE:
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		elif event.keycode >= KEY_1 and event.keycode <= KEY_9:
			_go_to(event.keycode - KEY_1)

func _physics_process(delta):
	var input = Vector2(
		Input.get_action_strength("ui_right") + float(Input.is_key_pressed(KEY_D)) - Input.get_action_strength("ui_left") - float(Input.is_key_pressed(KEY_A)),
		Input.get_action_strength("ui_down") + float(Input.is_key_pressed(KEY_S)) - Input.get_action_strength("ui_up") - float(Input.is_key_pressed(KEY_W)),
	).limit_length(1.0)
	var sprint = Input.is_key_pressed(KEY_SHIFT)
	var speed = walk_speed * (SPRINT if sprint else 1.0)
	var direction = (player.transform.basis * Vector3(input.x, 0, input.y)).normalized()
	player.velocity.x = direction.x * speed
	player.velocity.z = direction.z * speed
	if player.is_on_floor():
		player.velocity.y = 4.0 if Input.is_key_pressed(KEY_SPACE) else 0.0
	else:
		player.velocity.y -= 9.8 * delta
	player.move_and_slide()

	if input.length() > 0 and not timing:
		timing = true
	if timing:
		timer += delta
		sprinted = sprinted or (sprint and input.length() > 0)
	_update_hud()

func _update_hud():
	var nearest = ""
	var best = INF
	for anchor in landmarks:
		var d = Vector2(anchor.global_position.x - player.global_position.x, anchor.global_position.z - player.global_position.z).length()
		if d < best:
			best = d
			nearest = anchor.name
	var keys = ""
	for i in landmarks.size():
		keys += "  %d %s" % [i + 1, landmarks[i].name]
	var minutes = int(timer) / 60
	hud.text = "%s   from %s: %d:%04.1f%s\nnearest %s, %.0f m away   height %.1f m\nWASD walk at %.1f m/s · Shift sprint · Space jump · Esc frees the mouse\nJump to a Landmark and restart the timer:%s" % [
		site, from, minutes, fmod(timer, 60.0), "  (sprinted)" if sprinted else "",
		nearest, best, player.global_position.y - 0.9, walk_speed, keys]
