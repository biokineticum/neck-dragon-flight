extends Node3D

const Terrain = preload("res://scripts/ProceduralMeshGen.gd")
const VILLAGES: Array[Vector2] = Terrain.SETTLEMENT_CENTERS
const VILLAGE_CLEARANCE: float = 95.0

var world_size: float
var resolution: int
var seed_value: int
var animals: Array[Node3D] = []
var elapsed: float = 0.0

static func near_village(point: Vector2, size: float, padding: float = 0.0) -> bool:
	if size < 1600.0:
		return false
	for center in VILLAGES:
		if point.distance_to(center) < VILLAGE_CLEARANCE + padding:
			return true
	return false

func build(size: float, terrain_resolution: int, seed_val: int, forest_positions: PackedVector3Array) -> void:
	world_size = size
	resolution = terrain_resolution
	seed_value = seed_val
	if size >= 1600.0:
		_build_villages()
	_build_animals(forest_positions)

func _height(point: Vector2) -> float:
	return Terrain.sample_landscape_surface(point.x, point.y, world_size, resolution, seed_value)

func _material(color: Color) -> StandardMaterial3D:
	var material = StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.95
	return material

func _box(size: Vector3) -> BoxMesh:
	var mesh = BoxMesh.new()
	mesh.size = size
	return mesh

func _part(parent: Node3D, mesh: Mesh, material: Material, location: Vector3) -> MeshInstance3D:
	var instance = MeshInstance3D.new()
	instance.mesh = mesh
	instance.material_override = material
	instance.position = location
	parent.add_child(instance)
	return instance

func _build_villages() -> void:
	var settlements = Node3D.new()
	settlements.name = "Settlements"
	add_child(settlements)
	var walls = _material(Color(0.75, 0.65, 0.47))
	var wood = _material(Color(0.32, 0.19, 0.12))
	var roof_material = _material(Color(0.51, 0.24, 0.15))
	var window = _material(Color(0.12, 0.19, 0.20))
	var stone = _material(Color(0.39, 0.37, 0.32))
	var body = _box(Vector3(11.0, 7.0, 9.0))
	var roof = PrismMesh.new()
	roof.size = Vector3(12.5, 4.0, 10.5)
	var door = _box(Vector3(1.7, 3.2, 0.18))
	var glass = _box(Vector3(1.4, 1.4, 0.18))
	var chimney = _box(Vector3(1.4, 3.8, 1.4))
	var well_base = CylinderMesh.new()
	well_base.top_radius = 3.2
	well_base.bottom_radius = 3.2
	well_base.height = 1.8
	well_base.radial_segments = 12
	var well_water = CylinderMesh.new()
	well_water.top_radius = 2.4
	well_water.bottom_radius = 2.4
	well_water.height = 0.1
	well_water.radial_segments = 12
	var post = _box(Vector3(0.5, 4.0, 0.5))
	var well_roof = PrismMesh.new()
	well_roof.size = Vector3(7.5, 2.0, 5.0)
	var rng = RandomNumberGenerator.new()
	rng.seed = seed_value + 4429
	for village_index in range(VILLAGES.size()):
		var village = Node3D.new()
		village.name = "Village%d" % (village_index + 1)
		settlements.add_child(village)
		var center = VILLAGES[village_index]
		var well = Node3D.new()
		well.name = "Well"
		well.position = Vector3(center.x, _height(center), center.y)
		village.add_child(well)
		_part(well, well_base, stone, Vector3(0, 0.9, 0))
		_part(well, well_water, window, Vector3(0, 1.82, 0))
		_part(well, post, wood, Vector3(-2.7, 3.3, 0))
		_part(well, post, wood, Vector3(2.7, 3.3, 0))
		_part(well, well_roof, roof_material, Vector3(0, 6.0, 0))
		for i in range(7):
			var angle = TAU * float(i) / 7.0 + rng.randf_range(-0.15, 0.15)
			var point = center + Vector2(cos(angle), sin(angle)) * rng.randf_range(38.0, 53.0)
			var low = _height(point)
			var high = low
			for offset in [Vector2(-8, -8), Vector2(-8, 8), Vector2(8, -8), Vector2(8, 8)]:
				var sample = _height(point + offset)
				low = minf(low, sample)
				high = maxf(high, sample)
			var house = Node3D.new()
			house.name = "House%d" % (i + 1)
			house.position = Vector3(point.x, high + 0.1, point.y)
			house.rotation.y = -angle + PI * 0.5
			house.set_meta("ground_low", low)
			village.add_child(house)
			var foundation_height = high - low + 1.0
			_part(house, _box(Vector3(11.5, foundation_height, 9.5)), stone, Vector3(0, -foundation_height * 0.5, 0))
			_part(house, body, walls, Vector3(0, 3.5, 0))
			_part(house, roof, roof_material, Vector3(0, 9.0, 0))
			_part(house, chimney, stone, Vector3(3.1, 9.2, -1.8))
			_part(house, door, wood, Vector3(0, 1.6, 4.57))
			_part(house, glass, window, Vector3(-3.3, 4.0, 4.57))
			_part(house, glass, window, Vector3(3.3, 4.0, 4.57))

func _build_animals(forest_positions: PackedVector3Array) -> void:
	var wildlife = Node3D.new()
	wildlife.name = "ForestAnimals"
	add_child(wildlife)
	if forest_positions.is_empty():
		return
	var rng = RandomNumberGenerator.new()
	rng.seed = seed_value + 11887
	var deer_material = _material(Color(0.52, 0.31, 0.17))
	var fox_material = _material(Color(0.75, 0.29, 0.09))
	var dark = _material(Color(0.19, 0.13, 0.10))
	var cream = _material(Color(0.91, 0.82, 0.68))
	var body_mesh = _box(Vector3(0.8, 0.85, 1.55))
	var leg_mesh = _box(Vector3(0.16, 0.85, 0.16))
	var head_mesh = _box(Vector3(0.48, 0.48, 0.62))
	var ear_mesh = _box(Vector3(0.14, 0.28, 0.14))
	var tail_mesh = _box(Vector3(0.4, 0.35, 0.85))
	var total = mini(32, forest_positions.size())
	for i in range(total):
		var placed = false
		var point = Vector2.ZERO
		for attempt in range(30):
			var tree = forest_positions[rng.randi_range(0, forest_positions.size() - 1)]
			var angle = rng.randf_range(0.0, TAU)
			point = Vector2(tree.x, tree.z) + Vector2(cos(angle), sin(angle)) * rng.randf_range(10.0, 22.0)
			if point.length() < 70.0 or near_village(point, world_size, 8.0):
				continue
			if point.distance_to(Terrain.LAKE_CENTER) < Terrain.LAKE_RADIUS + 35.0:
				continue
			if point.x > Terrain.RIVER_START and point.x < Terrain.RIVER_END and absf(point.y - Terrain.river_center_z(point.x)) < Terrain.RIVER_HALF_WIDTH + 30.0:
				continue
			var ground = _height(point)
			if ground < 10.0 or ground > 125.0 or absf(_height(point + Vector2(3, 0)) - ground) > 2.0 or absf(_height(point + Vector2(0, 3)) - ground) > 2.0:
				continue
			placed = true
			break
		if not placed:
			continue
		var deer = i % 2 == 0
		var animal = Node3D.new()
		animal.name = ("Deer" if deer else "Fox") + str(i)
		animal.position = Vector3(point.x, _height(point), point.y)
		animal.set_meta("home", point)
		animal.set_meta("phase", rng.randf_range(0.0, TAU))
		animal.set_meta("pace", rng.randf_range(0.15, 0.28))
		wildlife.add_child(animal)
		animals.append(animal)
		var coat = deer_material if deer else fox_material
		var scale_factor = 1.6 if deer else 1.0
		animal.scale = Vector3.ONE * scale_factor
		_part(animal, body_mesh, coat, Vector3(0, 1.1, 0))
		for x in [-0.28, 0.28]:
			for z in [-0.5, 0.5]:
				var leg = _part(animal, leg_mesh, dark, Vector3(x, 0.43, z))
				leg.set_meta("gait_phase", 0.0 if x * z > 0 else PI)
		_part(animal, head_mesh, coat, Vector3(0, 1.65, -0.9))
		_part(animal, _box(Vector3(0.3, 0.22, 0.25)), cream, Vector3(0, 1.55, -1.25))
		for x in [-0.21, 0.21]:
			_part(animal, ear_mesh, coat, Vector3(x, 2.02, -0.9))
		if deer:
			for x in [-0.18, 0.18]:
				var antler = _part(animal, _box(Vector3(0.1, 0.55, 0.1)), dark, Vector3(x, 2.28, -0.88))
				antler.rotation.z = -signf(x) * 0.25
				var branch = _part(animal, _box(Vector3(0.08, 0.32, 0.08)), dark, Vector3(x * 1.8, 2.38, -0.88))
				branch.rotation.z = -signf(x) * 0.65
		else:
			var tail = _part(animal, tail_mesh, coat, Vector3(0, 1.25, 1.1))
			tail.rotation.x = -0.35
			_part(animal, _box(Vector3(0.38, 0.32, 0.22)), cream, Vector3(0, 1.4, 1.48))

func _process(delta: float) -> void:
	elapsed = fposmod(elapsed + delta, 3600.0)
	for animal in animals:
		var home: Vector2 = animal.get_meta("home")
		var phase: float = animal.get_meta("phase") + elapsed * float(animal.get_meta("pace"))
		var point = home + Vector2(cos(phase), sin(phase)) * 2.5
		animal.position = Vector3(point.x, _height(point), point.y)
		animal.rotation.y = PI - phase
		for part in animal.get_children():
			if part.has_meta("gait_phase"):
				part.rotation.x = sin(elapsed * 3.0 + phase + float(part.get_meta("gait_phase"))) * 0.2
