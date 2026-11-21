extends SceneTree

# ==============================================================================
# test_milestone2_headless.gd - Programmatic Headless Test Suite for Milestone 2
# ==============================================================================
# Extends SceneTree to execute in Godot 4 headless mode:
# & "Godot_v4.7.2-stable_win64_console.exe" --headless --path . -s test/test_milestone2_headless.gd
# ==============================================================================

func _init() -> void:
	print("==================================================================")
	print("   STARTING MILESTONE 2 HEADLESS VERIFICATION TEST SUITE")
	print("==================================================================")
	
	# Watchdog timer: failsafe exit if tests hang
	var watchdog = create_timer(20.0)
	watchdog.timeout.connect(func():
		printerr("[FATAL] Watchdog timeout (20.0s) exceeded! Terminating with code 1.")
		quit(1)
	)
	
	var passed: bool = await run_milestone2_suite()
	if passed:
		print("==================================================================")
		print("   ALL MILESTONE 2 TESTS PASSED SUCCESSFULLY (Exit code 0)")
		print("==================================================================")
		quit(0)
	else:
		printerr("==================================================================")
		printerr("   MILESTONE 2 TESTS FAILED (Exit code 1)")
		printerr("==================================================================")
		quit(1)

func run_milestone2_suite() -> bool:
	var success = true
	
	# 1. Project Configuration Assertions
	success = assert_project_settings() and success
	success = assert_input_map() and success
	
	# 2. Procedural Mesh Generation Assertions
	success = assert_procedural_meshes() and success
	
	# 3. Materials Assertions
	success = assert_materials() and success
	
	# 4. ChunkManager & Streaming Corridor Assertions
	success = await assert_chunk_streaming() and success
	
	return success

func assert_project_settings() -> bool:
	print("\n--- [CHECK 1: Project Settings] ---")
	var w = ProjectSettings.get_setting("display/window/size/viewport_width")
	var h = ProjectSettings.get_setting("display/window/size/viewport_height")
	var resizable = ProjectSettings.get_setting("display/window/size/resizable")
	var hz = ProjectSettings.get_setting("physics/common/physics_ticks_per_second")
	var renderer = ProjectSettings.get_setting("rendering/renderer/rendering_method")
	var layer1 = ProjectSettings.get_setting("layer_names/3d_physics/layer_1")
	var layer2 = ProjectSettings.get_setting("layer_names/3d_physics/layer_2")
	
	print("  Viewport: %s x %s (Resizable: %s)" % [str(w), str(h), str(resizable)])
	print("  Physics rate: %s Hz" % str(hz))
	print("  Renderer: %s" % str(renderer))
	print("  3D Physics Layers: Layer 1 = '%s', Layer 2 = '%s'" % [str(layer1), str(layer2)])
	
	if w != 1280 or h != 720:
		printerr("  FAIL: Viewport size %sx%s != 1280x720" % [str(w), str(h)])
		return false
	if not resizable:
		printerr("  FAIL: Window resizable is not true")
		return false
	if hz != 60:
		printerr("  FAIL: Physics tick rate %s != 60" % str(hz))
		return false
	if layer1 != "Environment" or layer2 != "Player":
		printerr("  FAIL: Physics layer names mismatch (Layer 1='%s', Layer 2='%s')" % [str(layer1), str(layer2)])
		return false
		
	print("  [PASS] Project settings validated successfully.")
	return true

func assert_input_map() -> bool:
	print("\n--- [CHECK 2: InputMap Action Bindings] ---")
	var expected_actions = [
		"steer_pitch_up", "steer_pitch_down",
		"steer_yaw_left", "steer_yaw_right",
		"steer_roll_left", "steer_roll_right",
		"boost", "brake", "calibrate", "mode_toggle", "restart"
	]
	
	for act in expected_actions:
		if not InputMap.has_action(act):
			printerr("  FAIL: Missing InputMap action '%s'" % act)
			return false
		var events = InputMap.action_get_events(act)
		if events.is_empty():
			printerr("  FAIL: Action '%s' has 0 events bound" % act)
			return false
		print("  Action '%s': %d event(s) bound" % [act, events.size()])
		
	print("  [PASS] All 11 InputMap flight actions verified.")
	return true

func assert_procedural_meshes() -> bool:
	print("\n--- [CHECK 3: Procedural Mesh Generation] ---")
	var gen_script = load("res://scripts/ProceduralMeshGen.gd")
	if gen_script == null:
		printerr("  FAIL: scripts/ProceduralMeshGen.gd could not be loaded")
		return false
		
	# 1. Dragon Head
	var head: ArrayMesh = gen_script.generate_dragon_head()
	if head == null or head.get_surface_count() == 0:
		printerr("  FAIL: generate_dragon_head() returned null or empty mesh")
		return false
	var head_aabb = head.get_aabb()
	print("  Dragon Head: %d surface(s), AABB %s" % [head.get_surface_count(), str(head_aabb)])
	if not _verify_mesh_normals(head):
		printerr("  FAIL: Dragon Head normal verification failed")
		return false
		
	# 2. Dragon Neck & Saddle
	var neck: ArrayMesh = gen_script.generate_dragon_neck_saddle()
	if neck == null or neck.get_surface_count() == 0:
		printerr("  FAIL: generate_dragon_neck_saddle() returned null or empty mesh")
		return false
	var neck_aabb = neck.get_aabb()
	print("  Dragon Neck/Saddle: %d surface(s), AABB %s" % [neck.get_surface_count(), str(neck_aabb)])
	if not _verify_mesh_normals(neck):
		printerr("  FAIL: Dragon Neck/Saddle normal verification failed")
		return false
		
	# 3. Dragon Wings (Left and Right)
	var wing_l: ArrayMesh = gen_script.generate_dragon_wing(true)
	var wing_r: ArrayMesh = gen_script.generate_dragon_wing(false)
	if wing_l == null or wing_l.get_surface_count() == 0 or wing_r == null or wing_r.get_surface_count() == 0:
		printerr("  FAIL: generate_dragon_wing() returned null or empty mesh")
		return false
	var aabb_l = wing_l.get_aabb()
	var aabb_r = wing_r.get_aabb()
	print("  Left Wing: AABB %s (min X = %.2f)" % [str(aabb_l), aabb_l.position.x])
	print("  Right Wing: AABB %s (max X = %.2f)" % [str(aabb_r), aabb_r.position.x + aabb_r.size.x])
	if aabb_l.position.x > -1.0 or (aabb_r.position.x + aabb_r.size.x) < 1.0:
		printerr("  FAIL: Wing lateral spans do not extend into cockpit periphery")
		return false
	if not _verify_mesh_normals(wing_l) or not _verify_mesh_normals(wing_r):
		printerr("  FAIL: Dragon Wing normal verification failed")
		return false
		
	# 4. Needle Spire
	var spire: ArrayMesh = gen_script.generate_needle_spire(60.0, 7.0, 42)
	if spire == null or spire.get_surface_count() == 0:
		printerr("  FAIL: generate_needle_spire() returned null or empty mesh")
		return false
	var spire_shape = spire.create_trimesh_shape()
	if spire_shape == null or not (spire_shape is ConcavePolygonShape3D):
		printerr("  FAIL: spire.create_trimesh_shape() did not produce ConcavePolygonShape3D")
		return false
	var spire_faces = spire_shape.get_faces()
	print("  Needle Spire: AABB %s, %d collision triangles" % [str(spire.get_aabb()), spire_faces.size() / 3])
	if spire_faces.size() < 30:
		printerr("  FAIL: Spire collision trimesh has too few triangles")
		return false
	if not _verify_mesh_normals(spire):
		printerr("  FAIL: Needle Spire normal verification failed")
		return false
	# Assert 0 degenerate zero-area triangles
	var degen_count = 0
	for i in range(0, spire_faces.size(), 3):
		var v0 = spire_faces[i]
		var v1 = spire_faces[i + 1]
		var v2 = spire_faces[i + 2]
		var cross_vec = (v1 - v0).cross(v2 - v0)
		if cross_vec.length() <= 0.0001:
			degen_count += 1
	print("  Needle Spire: %d / %d triangles have non-zero area (degenerate: %d)" % [spire_faces.size() / 3 - degen_count, spire_faces.size() / 3, degen_count])
	if degen_count > 0:
		printerr("  FAIL: Needle Spire has %d degenerate triangles (cross.length <= 0.0001)" % degen_count)
		return false
		
	# 5. Rock Arch
	var arch: ArrayMesh = gen_script.generate_rock_arch(42.0, 24.0, 42)
	if arch == null or arch.get_surface_count() == 0:
		printerr("  FAIL: generate_rock_arch() returned null or empty mesh")
		return false
	var arch_shape = arch.create_trimesh_shape()
	if arch_shape == null or not (arch_shape is ConcavePolygonShape3D):
		printerr("  FAIL: arch.create_trimesh_shape() did not produce ConcavePolygonShape3D")
		return false
	var arch_faces = arch_shape.get_faces()
	print("  Rock Arch: AABB %s, %d collision triangles" % [str(arch.get_aabb()), arch_faces.size() / 3])
	if arch_faces.size() < 30:
		printerr("  FAIL: Arch collision trimesh has too few triangles")
		return false
	if not _verify_mesh_normals(arch):
		printerr("  FAIL: Rock Arch normal verification failed")
		return false
	# Verify rock arch normals face outward (|Z| faces have outward direction)
	var arch_arrays = arch.surface_get_arrays(0)
	var arch_verts: PackedVector3Array = arch_arrays[Mesh.ARRAY_VERTEX]
	var arch_norms: PackedVector3Array = arch_arrays[Mesh.ARRAY_NORMAL]
	var arch_inward_z = 0
	var arch_outward_z = 0
	for i in range(arch_verts.size()):
		var v = arch_verts[i]
		var n = arch_norms[i]
		if abs(v.z) > 0.5:
			# Tube center is at z=0. For outward normal, normal.z has same sign as v.z:
			if (v.z * n.z) > 0.1:
				arch_outward_z += 1
			elif (v.z * n.z) < -0.1:
				arch_inward_z += 1
	print("  Rock Arch outward normals (|Z| > 0.5): outward=%d, inward=%d" % [arch_outward_z, arch_inward_z])
	if arch_inward_z > 0 or arch_outward_z == 0:
		printerr("  FAIL: Rock Arch normals face inward (%d inward, %d outward)" % [arch_inward_z, arch_outward_z])
		return false
	# Verify rock arch flight portal clearance (zero collision triangles intersecting [-10, 10] x [5, 15] at Z=0)
	var portal_hits = 0
	for i in range(0, arch_faces.size(), 3):
		var v0 = arch_faces[i]
		var v1 = arch_faces[i + 1]
		var v2 = arch_faces[i + 2]
		if min(v0.z, min(v1.z, v2.z)) <= 0.0 and max(v0.z, max(v1.z, v2.z)) >= 0.0:
			var mid = (v0 + v1 + v2) / 3.0
			if mid.x >= -10.0 and mid.x <= 10.0 and mid.y >= 5.0 and mid.y <= 15.0:
				portal_hits += 1
	print("  Rock Arch (span=42, clearance=24) flight portal [-10, 10] x [5, 15] hits: %d" % portal_hits)
	if portal_hits > 0:
		printerr("  FAIL: Rock Arch has %d collision triangles intersecting center flight portal" % portal_hits)
		return false
	# Also verify ChunkManager difficulty tiers (Tier 1: 45/26, Tier 2: 42/24, Tier 3: 40/22)
	var tier_configs = [
		{"tier": "Tier 1", "span": 45.0, "clearance": 26.0},
		{"tier": "Tier 2", "span": 42.0, "clearance": 24.0},
		{"tier": "Tier 3", "span": 40.0, "clearance": 22.0}
	]
	for cfg in tier_configs:
		var t_arch = gen_script.generate_rock_arch(cfg["span"], cfg["clearance"], 42)
		var t_faces = t_arch.create_trimesh_shape().get_faces()
		var t_hits = 0
		for i in range(0, t_faces.size(), 3):
			var v0 = t_faces[i]
			var v1 = t_faces[i + 1]
			var v2 = t_faces[i + 2]
			if min(v0.z, min(v1.z, v2.z)) <= 0.0 and max(v0.z, max(v1.z, v2.z)) >= 0.0:
				var mid = (v0 + v1 + v2) / 3.0
				if mid.x >= -10.0 and mid.x <= 10.0 and mid.y >= 5.0 and mid.y <= 15.0:
					t_hits += 1
		print("  Rock Arch %s (span=%.1f, clearance=%.1f) flight portal hits: %d" % [cfg["tier"], cfg["span"], cfg["clearance"], t_hits])
		if t_hits > 0:
			printerr("  FAIL: %s arch has %d collision triangles intersecting center flight portal" % [cfg["tier"], t_hits])
			return false
		
	# 6. Canyon Walls
	var canyon: ArrayMesh = gen_script.generate_canyon_walls(200.0, 85.0, 130.0, 42)
	if canyon == null or canyon.get_surface_count() == 0:
		printerr("  FAIL: generate_canyon_walls() returned null or empty mesh")
		return false
	var canyon_shape = canyon.create_trimesh_shape()
	if canyon_shape == null or not (canyon_shape is ConcavePolygonShape3D):
		printerr("  FAIL: canyon.create_trimesh_shape() did not produce ConcavePolygonShape3D")
		return false
	var canyon_faces = canyon_shape.get_faces()
	print("  Canyon Walls: AABB %s, %d collision triangles" % [str(canyon.get_aabb()), canyon_faces.size() / 3])
	if canyon_faces.size() < 30:
		printerr("  FAIL: Canyon collision trimesh has too few triangles")
		return false
	if not _verify_mesh_normals(canyon):
		printerr("  FAIL: Canyon Walls normal verification failed")
		return false
	# Verify canyon wall inward-facing normals (left wall +X > 0.1, right wall -X < -0.1)
	var canyon_arrays = canyon.surface_get_arrays(0)
	var canyon_norms: PackedVector3Array = canyon_arrays[Mesh.ARRAY_NORMAL]
	var left_inward = 0
	var left_inverted = 0
	for i in range(105):
		if canyon_norms[i].x > 0.1:
			left_inward += 1
		elif canyon_norms[i].x < -0.1:
			left_inverted += 1
	var right_inward = 0
	var right_inverted = 0
	for i in range(105, 210):
		if canyon_norms[i].x < -0.1:
			right_inward += 1
		elif canyon_norms[i].x > 0.1:
			right_inverted += 1
	print("  Canyon Left Wall inward normals (+X > 0.1): %d/105 (inverted: %d)" % [left_inward, left_inverted])
	print("  Canyon Right Wall inward normals (-X < -0.1): %d/105 (inverted: %d)" % [right_inward, right_inverted])
	if left_inverted > 0 or left_inward < 80:
		printerr("  FAIL: Canyon left wall normals do not point into corridor (+X)")
		return false
	if right_inverted > 0 or right_inward < 80:
		printerr("  FAIL: Canyon right wall normals do not point into corridor (-X)")
		return false
		
	print("  [PASS] All 6 procedural ArrayMesh generators verified.")
	return true

func _verify_mesh_normals(mesh: ArrayMesh) -> bool:
	for s in range(mesh.get_surface_count()):
		var arrays = mesh.surface_get_arrays(s)
		var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var norms: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		if norms.is_empty():
			printerr("    Surface %d has empty normal array" % s)
			return false
		if verts.size() != norms.size():
			printerr("    Surface %d vertex count (%d) != normal count (%d)" % [s, verts.size(), norms.size()])
			return false
		for i in range(norms.size()):
			var n: Vector3 = norms[i]
			if is_nan(n.x) or is_nan(n.y) or is_nan(n.z):
				printerr("    Surface %d normal %d is NaN" % [s, i])
				return false
			var len_sq = n.length_squared()
			if len_sq < 0.85 or len_sq > 1.15:
				printerr("    Surface %d normal %d not normalized: len=%.4f" % [s, i, sqrt(len_sq)])
				return false
	return true

func assert_materials() -> bool:
	print("\n--- [CHECK 4: Shaders and Materials] ---")
	
	# 1. Rock/Snow Triplanar Material
	var mat_rock = load("res://materials/rock_snow_triplanar.tres")
	if mat_rock == null:
		printerr("  FAIL: materials/rock_snow_triplanar.tres failed to load")
		return false
	if not (mat_rock is ShaderMaterial):
		printerr("  FAIL: rock_snow_triplanar.tres is not a ShaderMaterial")
		return false
	if mat_rock.shader == null:
		printerr("  FAIL: rock_snow_triplanar.tres has null shader")
		return false
	print("  rock_snow_triplanar.tres: ShaderMaterial loaded successfully")
	
	# 2. Dragon Scales Material
	var mat_dragon = load("res://materials/dragon_scales.tres")
	if mat_dragon == null:
		printerr("  FAIL: materials/dragon_scales.tres failed to load")
		return false
	if not (mat_dragon is StandardMaterial3D):
		printerr("  FAIL: dragon_scales.tres is not a StandardMaterial3D")
		return false
	if not mat_dragon.rim_enabled:
		printerr("  FAIL: dragon_scales.tres does not have rim_enabled")
		return false
	print("  dragon_scales.tres: StandardMaterial3D loaded successfully (Rim enabled)")
	
	# 3. Sky Environment
	var env_sky = load("res://materials/sky_environment.tres")
	if env_sky == null:
		printerr("  FAIL: materials/sky_environment.tres failed to load")
		return false
	if not (env_sky is Environment):
		printerr("  FAIL: sky_environment.tres is not an Environment")
		return false
	if env_sky.sky == null:
		printerr("  FAIL: sky_environment.tres has null sky")
		return false
	if not env_sky.fog_enabled:
		printerr("  FAIL: sky_environment.tres does not have fog_enabled")
		return false
	print("  sky_environment.tres: Environment loaded successfully (Sky + Fog enabled)")
	
	print("  [PASS] All 3 materials/environment resources verified.")
	return true

func assert_chunk_streaming() -> bool:
	print("\n--- [CHECK 5: ChunkManager Corridor Streaming] ---")
	var chunk_mgr_script = load("res://scripts/ChunkManager.gd")
	if chunk_mgr_script == null:
		printerr("  FAIL: scripts/ChunkManager.gd not found")
		return false
		
	var chunk_mgr: Node3D = chunk_mgr_script.new()
	root.add_child(chunk_mgr)
	await process_frame
	await physics_frame
	
	# Verify 4 chunks generated
	var chunk_count: int = chunk_mgr.get_active_chunk_count()
	print("  Active chunk count: %d" % chunk_count)
	if chunk_count != 4:
		printerr("  FAIL: ChunkManager active chunk count is %d (expected 4)" % chunk_count)
		chunk_mgr.free()
		return false
		
	# Verify corridor coverage across Z
	for i in range(chunk_count):
		var chunk: Node3D = chunk_mgr.chunk_pool[i]
		var expected_z = -float(i) * 200.0
		if abs(chunk.position.z - expected_z) > 0.01:
			printerr("  FAIL: Chunk %d at Z=%.2f (expected %.2f)" % [i, chunk.position.z, expected_z])
			chunk_mgr.free()
			return false
			
		# Check collision bodies in each chunk
		var static_bodies = chunk.find_children("", "StaticBody3D", true, false)
		if static_bodies.is_empty():
			printerr("  FAIL: Chunk %d has 0 StaticBody3D obstacles" % i)
			chunk_mgr.free()
			return false
			
		for sb in static_bodies:
			var body: StaticBody3D = sb
			if (body.collision_layer & 1) == 0:
				printerr("  FAIL: StaticBody3D '%s' in chunk %d not on Collision Layer 1" % [body.name, i])
				chunk_mgr.free()
				return false
				
	print("  Initial 4 chunks verified at Z = [0, -200, -400, -600] with Layer 1 collision.")
	
	# Test chunk recycling when player flies past rear chunk boundary
	print("  Simulating player flight to Z = -250.0 (past rear chunk boundary)...")
	chunk_mgr.update_player_position(Vector3(0, 20.0, -250.0))
	await process_frame
	
	# Front Z should now be -800.0
	if abs(chunk_mgr.current_front_z - (-800.0)) > 0.01:
		printerr("  FAIL: current_front_z is %.2f (expected -800.0)" % chunk_mgr.current_front_z)
		chunk_mgr.free()
		return false
		
	# Rear chunk should now be at -800.0
	var recycled_chunk: Node3D = chunk_mgr.chunk_pool[3]
	if abs(recycled_chunk.position.z - (-800.0)) > 0.01:
		printerr("  FAIL: Recycled chunk position Z is %.2f (expected -800.0)" % recycled_chunk.position.z)
		chunk_mgr.free()
		return false
	print("  Chunk successfully recycled and repositioned to Z = -800.0.")
	
	# Test reset_corridor() restores pristine state
	chunk_mgr.reset_corridor()
	await process_frame
	if chunk_mgr.get_active_chunk_count() != 4 or abs(chunk_mgr.chunk_pool[0].position.z) > 0.01:
		printerr("  FAIL: reset_corridor() did not restore initial corridor state")
		chunk_mgr.free()
		return false
	print("  reset_corridor() deterministically restored corridor.")
	
	# Cleanup
	chunk_mgr.free()
	print("  [PASS] ChunkManager corridor streaming and recycling fully verified.")
	return true
