extends Node3D

const Terrain = preload("res://scripts/ProceduralMeshGen.gd")
const GOAL: int = 5
const HEART_COUNT: int = 5
const PICKUP_RADIUS: float = 6.0
const MAX_DISTANCE: float = 750.0
const MIN_HEART_SPACING: float = 150.0
const FIREWORK_DURATION: float = 4.0

var player: CharacterBody3D
var game_manager: Node
var hud: CanvasLayer
var world: Node
var hearts: Array[Node3D] = []
var collected: int = 0
var previous_position: Vector3
var elapsed: float = 0.0
var firework_time: float = -1.0
var firework_root: Node3D
var sparks: Array[Dictionary] = []
var heart_mesh: ArrayMesh
var heart_material: StandardMaterial3D
var spark_mesh: SphereMesh
var spark_materials: Array[StandardMaterial3D] = []

func _ready() -> void:
	player = get_node("../PlayerDragon") as CharacterBody3D
	game_manager = get_node("../GameManager")
	hud = get_node("../HUD") as CanvasLayer
	world = get_node("../ChunkManager")
	heart_mesh = _make_heart_mesh()
	heart_material = _emissive_material(Color(1.0, 0.16, 0.34), 1.2)
	spark_mesh = SphereMesh.new()
	spark_mesh.radius = 0.85
	spark_mesh.height = 1.7
	for color in [Color(1.0, 0.2, 0.37), Color(1.0, 0.72, 0.15), Color(0.35, 0.8, 1.0), Color(0.83, 0.4, 1.0), Color(0.45, 1.0, 0.6)]:
		spark_materials.append(_emissive_material(color, 2.0))
	game_manager.game_restarted.connect(reset)
	reset()

func reset() -> void:
	collected = 0
	elapsed = 0.0
	previous_position = player.global_position
	for heart in hearts:
		heart.queue_free()
	hearts.clear()
	_clear_fireworks()
	for i in range(HEART_COUNT):
		var heart = Node3D.new()
		heart.name = "Heart%d" % (i + 1)
		add_child(heart)
		var visual = MeshInstance3D.new()
		visual.mesh = heart_mesh
		visual.material_override = heart_material
		heart.add_child(visual)
		hearts.append(heart)
		_place_heart(heart, i)
	_update_hud()

func _physics_process(delta: float) -> void:
	elapsed += delta
	var current_position = player.global_position
	if game_manager.get_state() == game_manager.GameState.FLYING:
		for i in range(hearts.size()):
			var heart = hearts[i]
			var nearest = Geometry3D.get_closest_point_to_segment(heart.global_position, previous_position, current_position)
			if nearest.distance_to(heart.global_position) <= PICKUP_RADIUS:
				_collect_heart(heart, i)
			elif heart.global_position.distance_to(current_position) > MAX_DISTANCE:
				_place_heart(heart, i)
			var toward_player = current_position - heart.global_position
			heart.rotation.y = atan2(toward_player.x, toward_player.z) + sin(elapsed * 0.8 + i) * 0.15
			heart.scale = Vector3.ONE * (1.0 + 0.08 * sin(elapsed * 2.5 + i))
	previous_position = current_position
	_update_fireworks(delta)

func _place_heart(heart: Node3D, index: int) -> void:
	var forward = -player.global_basis.z
	forward.y = 0.0
	forward = forward.normalized()
	if forward.length_squared() < 0.1:
		forward = Vector3.FORWARD
	var origin = player.global_position
	var base_angle: float = [0.0, 0.95, -0.95, 1.9, -1.9][index]
	var distance: float = [220.0, 270.0, 320.0, 370.0, 420.0][index]
	var target = origin
	var best_spacing = -1.0
	for attempt in range(16):
		var direction = forward.rotated(Vector3.UP, base_angle + attempt * TAU / 16.0)
		var candidate = origin + direction * distance
		if Vector2(candidate.x, candidate.z).length() > world.soft_boundary_radius - 80.0:
			continue
		var spacing = INF
		for other in hearts:
			if other != heart:
				spacing = minf(spacing, Vector2(candidate.x, candidate.z).distance_to(Vector2(other.global_position.x, other.global_position.z)))
		if spacing > best_spacing:
			best_spacing = spacing
			target = candidate
		if spacing >= MIN_HEART_SPACING:
			break
	if best_spacing < 0.0:
		var inward = Vector3(-origin.x, 0.0, -origin.z).normalized()
		target = origin + inward * distance
	var ground = Terrain.sample_landscape_surface(target.x, target.z, world.world_size, world.world_resolution, world.master_seed)
	target.y = maxf(origin.y + [0.0, 8.0, -5.0, 18.0, 10.0][index], ground + 22.0)
	heart.global_position = target

func _collect_heart(heart: Node3D, index: int) -> void:
	if collected == GOAL:
		collected = 0
	collected += 1
	_update_hud()
	_place_heart(heart, index)
	if collected == GOAL:
		_start_fireworks()

func _update_hud() -> void:
	hud.update_collectible_hearts(collected, GOAL)

func _emissive_material(color: Color, energy: float) -> StandardMaterial3D:
	var material = StandardMaterial3D.new()
	material.albedo_color = color
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = energy
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return material

func _make_heart_mesh() -> ArrayMesh:
	var outline = PackedVector2Array()
	for i in range(48):
		var t = TAU * float(i) / 48.0
		var x = 16.0 * pow(sin(t), 3.0) / 6.0
		var y = (13.0 * cos(t) - 5.0 * cos(2.0 * t) - 2.0 * cos(3.0 * t) - cos(4.0 * t)) / 6.0
		outline.append(Vector2(x, y))
	var triangles = Geometry2D.triangulate_polygon(outline)
	var surface = SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	# Front, back, and rim give the silhouette depth from either direction.
	for j in range(0, triangles.size(), 3):
		for k in range(3):
			var p = outline[triangles[j + k]]
			surface.add_vertex(Vector3(p.x, p.y, 0.55))
		for k in [2, 1, 0]:
			var p = outline[triangles[j + k]]
			surface.add_vertex(Vector3(p.x, p.y, -0.55))
	for i in range(outline.size()):
		var a = outline[i]
		var b = outline[(i + 1) % outline.size()]
		for p in [Vector3(a.x, a.y, 0.55), Vector3(b.x, b.y, 0.55), Vector3(b.x, b.y, -0.55), Vector3(a.x, a.y, 0.55), Vector3(b.x, b.y, -0.55), Vector3(a.x, a.y, -0.55)]:
			surface.add_vertex(p)
	surface.generate_normals()
	return surface.commit()

func _start_fireworks() -> void:
	_clear_fireworks()
	firework_time = 0.0
	firework_root = Node3D.new()
	firework_root.name = "Fireworks"
	add_child(firework_root)
	var rng = RandomNumberGenerator.new()
	rng.seed = int(Time.get_ticks_usec())
	for burst in range(5):
		for i in range(24):
			var spark = MeshInstance3D.new()
			spark.mesh = spark_mesh
			spark.material_override = spark_materials[burst % spark_materials.size()]
			spark.visible = false
			firework_root.add_child(spark)
			var angle = TAU * float(i) / 24.0
			spark.rotation.z = angle - PI * 0.5
			var direction = Vector3(cos(angle), sin(angle), rng.randf_range(-0.25, 0.25)).normalized()
			sparks.append({"node": spark, "burst": burst, "direction": direction, "speed": rng.randf_range(10.0, 17.0)})

func _update_fireworks(delta: float) -> void:
	if firework_time < 0.0:
		return
	firework_time += delta
	if firework_time >= FIREWORK_DURATION:
		_clear_fireworks()
		return
	firework_root.global_transform = player.global_transform
	for data in sparks:
		var age: float = firework_time - float(data.burst) * 0.4
		var spark: MeshInstance3D = data.node
		spark.visible = age >= 0.0 and age < 1.9
		if spark.visible:
			var center = Vector3((float(data.burst) - 2.0) * 13.0, 14.0 + (data.burst % 2) * 8.0, -85.0)
			spark.position = center + data.direction * data.speed * age + Vector3.DOWN * 3.0 * age * age
			spark.scale = Vector3(0.7, 2.0, 0.7) * maxf(0.08, 1.0 - age / 1.9)

func _clear_fireworks() -> void:
	if is_instance_valid(firework_root):
		firework_root.queue_free()
	firework_root = null
	firework_time = -1.0
	sparks.clear()
