extends SceneTree
# Walks a CharacterBody3D along every Path curve of one exported Site, on Godot's
# own collision, at the Brief's Walk Speed measured along the ground (as the Checks do).

const SPEED = 1.4
const GRAVITY = 9.8
const HALF_HEIGHT = 0.9  # capsule centre above its feet

var body
var curves = []  # [name, PackedVector3Array]
var current = -1
var points
var next_point
var ticks
var lowest
var highest
var last_progress_tick

func _initialize():
	var scene_name = OS.get_cmdline_user_args()[0]
	var scene = load("res://%s.tscn" % scene_name).instantiate()
	root.add_child(scene)
	for path in scene.find_child("paths", true, false).get_children():
		curves.append([path.name, path.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]])
	body = CharacterBody3D.new()
	var shape = CollisionShape3D.new()
	shape.shape = CapsuleShape3D.new()
	shape.shape.radius = 0.4
	shape.shape.height = 1.8
	body.add_child(shape)
	body.floor_snap_length = 0.5
	root.add_child(body)
	_start_next()

func _start_next():
	current += 1
	if current >= curves.size():
		quit()
		return
	points = curves[current][1]
	next_point = 1
	ticks = 0
	lowest = INF
	highest = -INF
	last_progress_tick = 0
	body.position = points[0] + Vector3.UP * (HALF_HEIGHT + 0.05)
	body.velocity = Vector3.ZERO

func _physics_process(delta):
	if current >= curves.size():
		return true
	ticks += 1
	var target = points[next_point]
	var from = points[next_point - 1]
	var flat = Vector2(target.x - body.global_position.x, target.z - body.global_position.z)
	if flat.length() < 0.15:
		next_point += 1
		last_progress_tick = ticks
		if next_point >= points.size():
			_report("arrived")
			_start_next()
			return false
		target = points[next_point]
		from = points[next_point - 1]
		flat = Vector2(target.x - body.global_position.x, target.z - body.global_position.z)
	# horizontal speed so that speed along the ground's slope is SPEED
	var segment = target - from
	var along = Vector2(segment.x, segment.z).length()
	var horizontal = SPEED * (along / segment.length() if segment.length() > 0 else 1.0)
	var direction = flat.normalized()
	body.velocity.x = direction.x * horizontal
	body.velocity.z = direction.y * horizontal
	body.velocity.y = 0.0 if body.is_on_floor() else body.velocity.y - GRAVITY * delta
	body.move_and_slide()
	# feet against the ground the curve says is under them
	var ground = from.lerp(target, clamp(1.0 - flat.length() / max(along, 0.001), 0.0, 1.0)).y
	var gap = body.global_position.y - HALF_HEIGHT - ground
	lowest = min(lowest, gap)
	highest = max(highest, gap)
	if gap < -1.0:
		_report("FELL THROUGH")
		_start_next()
	elif ticks - last_progress_tick > 600:
		_report("STUCK")
		_start_next()
	return false

func _report(outcome):
	print("%s: %s after %.1f s at point %d/%d; feet %.2f..%.2f m from the ground" % [
		curves[current][0], outcome, ticks / 60.0, next_point, points.size() - 1, lowest, highest])
