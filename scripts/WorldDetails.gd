extends Node3D

const Terrain = preload("res://scripts/ProceduralMeshGen.gd")
const WATER_SHADER = preload("res://materials/lake_water.gdshader")
const WATERFALL_SHADER = preload("res://materials/waterfall.gdshader")

var wind_player: AudioStreamPlayer
var birds: MultiMeshInstance3D

func build(world_size: float, resolution: int, seed_value: int) -> void:
	_build_boulders(world_size, resolution, seed_value)
	if world_size >= 1300.0:
		_build_lake()
		_build_landmarks(world_size, resolution, seed_value)
		_build_cave(world_size, resolution, seed_value)
	if world_size >= 2400.0:
		_build_river()
	_build_birds(world_size, seed_value)
	_build_wind(seed_value)
	_build_birdsong(world_size, resolution, seed_value)

func _build_lake() -> void:
	var st = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var segments = 64
	for i in range(segments):
		var a = TAU * float(i) / float(segments)
		var b = TAU * float(i + 1) / float(segments)
		st.add_vertex(Vector3.ZERO)
		st.add_vertex(Vector3(cos(b), 0.0, sin(b)) * Terrain.LAKE_RADIUS)
		st.add_vertex(Vector3(cos(a), 0.0, sin(a)) * Terrain.LAKE_RADIUS)
	st.generate_normals()
	var water = MeshInstance3D.new()
	water.name = "ValleyLake"
	water.mesh = st.commit()
	var material = ShaderMaterial.new()
	material.shader = WATER_SHADER
	water.material_override = material
	water.position = Vector3(Terrain.LAKE_CENTER.x, Terrain.LAKE_LEVEL, Terrain.LAKE_CENTER.y)
	add_child(water)

func _build_river() -> void:
	var material = ShaderMaterial.new()
	material.shader = WATER_SHADER
	for section in [Vector2(Terrain.RIVER_START + 20.0, Terrain.RIVER_FALL), Vector2(Terrain.RIVER_FALL + 0.1, Terrain.RIVER_END - 45.0)]:
		var st = SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		var segments = ceili((section.y - section.x) / 8.0)
		for i in range(segments):
			var x0 = lerpf(section.x, section.y, float(i) / segments)
			var x1 = lerpf(section.x, section.y, float(i + 1) / segments)
			var a = Vector3(x0, Terrain.river_level(x0), Terrain.river_center_z(x0) - Terrain.river_half_width(x0))
			var b = Vector3(x0, Terrain.river_level(x0), Terrain.river_center_z(x0) + Terrain.river_half_width(x0))
			var c = Vector3(x1, Terrain.river_level(x1), Terrain.river_center_z(x1) - Terrain.river_half_width(x1))
			var d = Vector3(x1, Terrain.river_level(x1), Terrain.river_center_z(x1) + Terrain.river_half_width(x1))
			st.add_vertex(a); st.add_vertex(d); st.add_vertex(c)
			st.add_vertex(a); st.add_vertex(b); st.add_vertex(d)
		st.generate_normals()
		var river = MeshInstance3D.new()
		river.name = "LowerRiver" if section.x < Terrain.RIVER_FALL else "UpperRiver"
		river.mesh = st.commit()
		river.material_override = material
		add_child(river)

	var fall = MeshInstance3D.new()
	fall.name = "Waterfall"
	var quad = QuadMesh.new()
	quad.size = Vector2(Terrain.river_half_width(Terrain.RIVER_FALL) * 2.0, 30.0)
	fall.mesh = quad
	var foam_material = ShaderMaterial.new()
	foam_material.shader = WATERFALL_SHADER
	fall.material_override = foam_material
	var low_level = Terrain.river_level(Terrain.RIVER_FALL)
	fall.position = Vector3(Terrain.RIVER_FALL, low_level + 15.0, Terrain.river_center_z(Terrain.RIVER_FALL))
	fall.rotation.y = PI * 0.5
	add_child(fall)

func _build_boulders(world_size: float, resolution: int, seed_value: int) -> void:
	var rocks = MultiMeshInstance3D.new()
	rocks.name = "Boulders"
	var mesh = SphereMesh.new()
	mesh.radius = 1.0
	mesh.height = 2.0
	mesh.radial_segments = 8
	mesh.rings = 4
	var mat = StandardMaterial3D.new()
	mat.albedo_color = Color(0.36, 0.37, 0.34)
	mat.roughness = 1.0
	mesh.material = mat
	var mm = MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = mesh
	mm.instance_count = 350
	var rng = RandomNumberGenerator.new()
	rng.seed = seed_value + 31237
	var half_size = world_size * 0.42
	var placed = 0
	for i in range(1400):
		if placed >= mm.instance_count:
			break
		var x = rng.randf_range(-half_size, half_size)
		var z = rng.randf_range(-half_size, half_size)
		if Vector2(x, z).length() < 180.0 or Vector2(x, z).distance_to(Terrain.LAKE_CENTER) < Terrain.LAKE_RADIUS + 20.0:
			continue
		if x > Terrain.RIVER_START and x < Terrain.RIVER_END and absf(z - Terrain.river_center_z(x)) < Terrain.RIVER_HALF_WIDTH + 20.0:
			continue
		var y = Terrain.sample_landscape_surface(x, z, world_size, resolution, seed_value)
		var radius = rng.randf_range(1.8, 6.0)
		var transform = Transform3D(Basis.from_scale(Vector3(radius, radius * rng.randf_range(0.5, 1.0), radius * rng.randf_range(0.7, 1.4))), Vector3(x, y, z))
		mm.set_instance_transform(placed, transform)
		placed += 1
	mm.visible_instance_count = placed
	rocks.multimesh = mm
	add_child(rocks)

func _build_landmarks(world_size: float, resolution: int, seed_value: int) -> void:
	var stone = StandardMaterial3D.new()
	stone.albedo_color = Color(0.46, 0.42, 0.36)
	stone.roughness = 0.95
	var tower = Node3D.new()
	tower.name = "Watchtower"
	tower.position = _surface_position(Vector2(-460.0, -480.0), world_size, resolution, seed_value)
	add_child(tower)
	var base = CylinderMesh.new()
	base.bottom_radius = 10.0
	base.top_radius = 7.0
	base.height = 38.0
	base.radial_segments = 12
	_add_mesh(tower, base, stone, Vector3(0, 17.0, 0))
	var crown = CylinderMesh.new()
	crown.bottom_radius = 9.0
	crown.top_radius = 9.0
	crown.height = 3.0
	crown.radial_segments = 12
	_add_mesh(tower, crown, stone, Vector3(0, 37.5, 0))
	for i in range(8):
		var angle = TAU * float(i) / 8.0
		var block = BoxMesh.new()
		block.size = Vector3(3.0, 4.0, 3.0)
		_add_mesh(tower, block, stone, Vector3(cos(angle) * 7.0, 40.0, sin(angle) * 7.0))

	var gate = Node3D.new()
	gate.name = "AncientGate"
	gate.position = _surface_position(Vector2(500.0, 410.0), world_size, resolution, seed_value)
	gate.rotation.y = -0.5
	add_child(gate)
	var pillar = BoxMesh.new()
	pillar.size = Vector3(6.0, 32.0, 6.0)
	_add_mesh(gate, pillar, stone, Vector3(-15.0, 14.0, 0.0))
	_add_mesh(gate, pillar, stone, Vector3(15.0, 14.0, 0.0))
	var lintel = BoxMesh.new()
	lintel.size = Vector3(36.0, 5.0, 7.0)
	_add_mesh(gate, lintel, stone, Vector3(0.0, 32.0, 0.0))

func _surface_position(point: Vector2, world_size: float, resolution: int, seed_value: int) -> Vector3:
	return Vector3(point.x, Terrain.sample_landscape_surface(point.x, point.y, world_size, resolution, seed_value), point.y)

func _build_cave(world_size: float, resolution: int, seed_value: int) -> void:
	var outer: Array[Vector2] = [Vector2(-23.0, -18.0), Vector2(-23.0, 0.0)]
	var inner: Array[Vector2] = [Vector2(-16.0, -18.0), Vector2(-16.0, 0.0)]
	for i in range(1, 13):
		var angle = PI - PI * float(i) / 12.0
		var irregularity = 1.0 + 0.11 * sin(float(i) * 4.1 + float(seed_value))
		outer.append(Vector2(cos(angle) * 23.0 * irregularity, sin(angle) * 22.0 * irregularity))
		inner.append(Vector2(cos(angle) * 16.0 * (1.0 + 0.025 * sin(float(i) * 3.0)), sin(angle) * 15.0))
	outer.append(Vector2(23.0, -18.0))
	inner.append(Vector2(16.0, -18.0))
	var st = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in range(outer.size() - 1):
		_cave_quad(st, outer[i], outer[i + 1], -28.0, 28.0)
		_cave_quad(st, inner[i + 1], inner[i], -28.0, 28.0)
		for end in [-28.0, 28.0]:
			var a = Vector3(outer[i].x, outer[i].y, end)
			var b = Vector3(outer[i + 1].x, outer[i + 1].y, end)
			var c = Vector3(inner[i + 1].x, inner[i + 1].y, end)
			var d = Vector3(inner[i].x, inner[i].y, end)
			st.add_vertex(a); st.add_vertex(b); st.add_vertex(c)
			st.add_vertex(a); st.add_vertex(c); st.add_vertex(d)
	st.generate_normals()
	var cave = MeshInstance3D.new()
	cave.name = "RockTunnel"
	cave.mesh = st.commit()
	var rock_material = ShaderMaterial.new()
	rock_material.shader = preload("res://materials/tunnel_rock.gdshader")
	cave.material_override = rock_material
	var location = Vector2(-630.0, 360.0)
	var ground = Terrain.sample_landscape_surface(location.x, location.y, world_size, resolution, seed_value)
	for offset in [Vector2(-20.0, -25.0), Vector2(20.0, -25.0), Vector2(-20.0, 25.0), Vector2(20.0, 25.0)]:
		ground = maxf(ground, Terrain.sample_landscape_surface(location.x + offset.x, location.y + offset.y, world_size, resolution, seed_value))
	cave.position = Vector3(location.x, ground + 5.0, location.y)
	add_child(cave)

func _cave_quad(st: SurfaceTool, a: Vector2, b: Vector2, z0: float, z1: float) -> void:
	var p0 = Vector3(a.x, a.y, z0)
	var p1 = Vector3(b.x, b.y, z0)
	var p2 = Vector3(b.x, b.y, z1)
	var p3 = Vector3(a.x, a.y, z1)
	st.add_vertex(p0); st.add_vertex(p1); st.add_vertex(p2)
	st.add_vertex(p0); st.add_vertex(p2); st.add_vertex(p3)

func _add_mesh(parent: Node3D, mesh: Mesh, material: Material, location: Vector3) -> void:
	var instance = MeshInstance3D.new()
	instance.mesh = mesh
	instance.material_override = material
	instance.position = location
	parent.add_child(instance)

func _build_birds(world_size: float, seed_value: int) -> void:
	var st = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	st.add_vertex(Vector3(-2.2, 0.35, 0.2))
	st.add_vertex(Vector3(0.0, 0.0, -0.5))
	st.add_vertex(Vector3(0.0, 0.0, 0.8))
	st.add_vertex(Vector3(2.2, 0.35, 0.2))
	st.add_vertex(Vector3(0.0, 0.0, 0.8))
	st.add_vertex(Vector3(0.0, 0.0, -0.5))
	st.generate_normals()
	var bird_mesh = st.commit()
	var material = StandardMaterial3D.new()
	material.albedo_color = Color(0.12, 0.15, 0.17)
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	bird_mesh.surface_set_material(0, material)
	var mm = MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = bird_mesh
	mm.instance_count = 18
	var rng = RandomNumberGenerator.new()
	rng.seed = seed_value + 4817
	var radius = minf(world_size * 0.25, 550.0)
	for i in range(mm.instance_count):
		var angle = TAU * float(i) / float(mm.instance_count) + rng.randf_range(-0.15, 0.15)
		var distance = radius + rng.randf_range(-30.0, 30.0)
		var position = Vector3(cos(angle) * distance, rng.randf_range(145.0, 200.0), sin(angle) * distance)
		mm.set_instance_transform(i, Transform3D(Basis(Vector3.UP, -angle), position))
	birds = MultiMeshInstance3D.new()
	birds.name = "DistantBirds"
	birds.multimesh = mm
	add_child(birds)

func _build_wind(seed_value: int) -> void:
	var sample_rate = 22050
	var count = sample_rate * 4
	var samples = PackedFloat32Array()
	samples.resize(count)
	var rng = RandomNumberGenerator.new()
	rng.seed = seed_value + 7817
	var filtered = 0.0
	for i in range(count):
		filtered = lerpf(filtered, rng.randf_range(-1.0, 1.0), 0.12)
		samples[i] = filtered
	# Crossfade the loop boundary to avoid clicks.
	var fade = sample_rate / 4
	for i in range(fade):
		var blend = float(i) / float(fade)
		samples[count - fade + i] = lerpf(samples[count - fade + i], samples[i], blend)
	var data = PackedByteArray()
	data.resize(count * 2)
	for i in range(count):
		data.encode_s16(i * 2, int(clampf(samples[i] * 24000.0, -32768.0, 32767.0)))
	var stream = AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = sample_rate
	stream.data = data
	stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
	stream.loop_begin = fade
	stream.loop_end = count
	wind_player = AudioStreamPlayer.new()
	wind_player.name = "WindAmbience"
	wind_player.stream = stream
	wind_player.volume_db = -34.0
	add_child(wind_player)
	if DisplayServer.get_name() != "headless":
		wind_player.play()
	if has_node("ValleyLake"):
		_add_water_sound("LakeAmbience", Vector3(Terrain.LAKE_CENTER.x, Terrain.LAKE_LEVEL, Terrain.LAKE_CENTER.y), stream)
	if has_node("Waterfall"):
		_add_water_sound("FallsAmbience", get_node("Waterfall").position, stream)

func _add_water_sound(sound_name: String, location: Vector3, stream: AudioStreamWAV) -> void:
	var player = AudioStreamPlayer3D.new()
	player.name = sound_name
	player.position = location
	player.stream = stream
	player.pitch_scale = 1.35
	player.volume_db = -20.0
	player.unit_size = 60.0
	player.max_distance = 250.0
	add_child(player)
	if DisplayServer.get_name() != "headless":
		player.play()

func _build_birdsong(world_size: float, resolution: int, seed_value: int) -> void:
	var sample_rate = 22050
	var count = sample_rate * 12
	var data = PackedByteArray()
	data.resize(count * 2)
	var rng = RandomNumberGenerator.new()
	rng.seed = seed_value + 5923
	for call_time in [1.0, 3.8, 7.0, 9.5]:
		var start = int((call_time + rng.randf_range(-0.2, 0.2)) * sample_rate)
		var duration = int(sample_rate * 0.16)
		var frequency = rng.randf_range(1500.0, 2100.0)
		for i in range(duration):
			var t = float(i) / sample_rate
			var envelope = pow(sin(PI * float(i) / duration), 2.0)
			var phase = TAU * (frequency * t + 1800.0 * t * t)
			data.encode_s16((start + i) * 2, int(sin(phase) * envelope * 8500.0))
	var stream = AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = sample_rate
	stream.data = data
	stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
	stream.loop_end = count
	var song = AudioStreamPlayer3D.new()
	song.name = "ForestAmbience"
	song.position = _surface_position(Vector2(-190.0, -170.0), world_size, resolution, seed_value) + Vector3.UP * 8.0
	song.stream = stream
	song.volume_db = -22.0
	song.unit_size = 70.0
	song.max_distance = 400.0
	add_child(song)
	if DisplayServer.get_name() != "headless":
		song.play()

func _process(delta: float) -> void:
	if birds != null:
		birds.rotate_y(delta * 0.018)
	var manager = get_parent()
	if wind_player == null or manager == null or manager.player_ref == null:
		return
	var controller = manager.player_ref.get_node_or_null("FlightController")
	if controller != null:
		var speed_ratio = clampf((controller.current_speed - 18.0) / 36.0, 0.0, 1.0)
		var altitude_ratio = clampf((manager.player_ref.global_position.y - 80.0) / 250.0, 0.0, 1.0)
		var target_db = lerpf(-38.0, -28.0, speed_ratio) + altitude_ratio * 3.0
		wind_player.volume_db = lerpf(wind_player.volume_db, target_db, 1.0 - exp(-2.0 * delta))
