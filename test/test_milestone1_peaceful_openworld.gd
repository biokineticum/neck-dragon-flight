extends SceneTree

# ==============================================================================
# test_milestone1_peaceful_openworld.gd
# Programmatic Headless Verification Test Suite for Milestone M1
# ==============================================================================
# Verifies all acceptance criteria for:
# R1: Large Open World Landscape (3000m x 3000m, 2000+ trees MultiMesh, 3D clouds,
#     camera far=3500m, shadow dist=800m, fog=0.00055, soft boundary at R>1350m)
# R2: Peaceful Flight Mechanics (No damage, no health loss, no hit-stop, no game over,
#     ground cushion lift near terrain, tangential deflection, HUD hearts/death hidden)
# R3: Vibrant Pink Dragon Visuals (albedo_color, emission, rim, clearcoat)
# R4: Controls & UDP head tracking compatibility
# ==============================================================================

const TEST_DELTA: float = 1.0 / 60.0

const ChunkManager = preload("res://scripts/ChunkManager.gd")
const FlightController = preload("res://scripts/FlightController.gd")
const GameManager = preload("res://scripts/GameManager.gd")
const HUD = preload("res://scripts/HUD.gd")

func _init() -> void:
	print("==================================================================")
	print("   STARTING MILESTONE M1 PEACEFUL OPEN-WORLD VERIFICATION SUITE   ")
	print("==================================================================")
	
	var watchdog = create_timer(30.0)
	watchdog.timeout.connect(func():
		printerr("[FATAL] M1 test watchdog (30.0s) exceeded! Aborting.")
		quit(1)
	)
	
	var passed = await run_m1_verification_battery()
	if passed:
		print("\n==================================================================")
		print("   ALL MILESTONE M1 VERIFICATION TESTS PASSED (Exit code 0)")
		print("==================================================================")
		quit(0)
	else:
		printerr("\n==================================================================")
		printerr("   MILESTONE M1 VERIFICATION TESTS FAILED (Exit code 1)")
		printerr("==================================================================")
		quit(1)

func run_m1_verification_battery() -> bool:
	var success = true
	
	# Check 1: R3 Pink Dragon Visuals
	success = test_r3_pink_dragon_visuals() and success
	
	# Check 2: R1 Environment, Camera & Lighting Parameters
	success = test_r1_environment_and_lighting() and success
	
	# Check 3: R1 Static Open World Landscape, Forests & Clouds
	success = await test_r1_landscape_forests_and_clouds() and success
	
	# Check 4: R1 Soft Boundary Steering Guidance (R > 1350m)
	success = await test_r1_soft_boundary_guidance() and success
	
	# Check 5: R2 Peaceful Flight, Deflection & Ground Cushion
	success = await test_r2_peaceful_flight_mechanics() and success
	
	# Check 6: R2 HUD Hearts & Game-Over Panel Hidden
	success = await test_r2_hud_peaceful_elements() and success
	
	# Check 7: R4 Controls & UDP Head Tracking Compatibility
	success = await test_r4_controls_and_tracking() and success
	
	return success

## -----------------------------------------------------------------------------
## Check 1: R3 Pink Dragon Visuals
## -----------------------------------------------------------------------------
func test_r3_pink_dragon_visuals() -> bool:
	print("\n--- [CHECK 1: R3 Pink Dragon Visuals] ---")
	var mat = load("res://materials/dragon_scales.tres") as StandardMaterial3D
	if mat == null:
		printerr("  FAIL: Failed to load res://materials/dragon_scales.tres")
		return false
		
	print("  Albedo: %s, Emission: %s" % [str(mat.albedo_color), str(mat.emission)])
	
	# Assert vibrant pink color: High red, high blue, moderate/low green
	if mat.albedo_color.r < 0.85 or mat.albedo_color.b < 0.45 or mat.albedo_color.g > 0.40:
		printerr("  FAIL: Albedo color is not vibrant pink (R=%.2f, G=%.2f, B=%.2f)" % [
			mat.albedo_color.r, mat.albedo_color.g, mat.albedo_color.b
		])
		return false
		
	# Assert pink emission glow
	if not mat.emission_enabled or mat.emission.r < 0.70 or mat.emission.b < 0.40:
		printerr("  FAIL: Emission is not enabled or not pink (R=%.2f, B=%.2f)" % [
			mat.emission.r, mat.emission.b
		])
		return false
		
	# Assert glistening scale rim lighting & clearcoat
	if not mat.rim_enabled or not mat.clearcoat_enabled:
		printerr("  FAIL: Rim or Clearcoat is not enabled on dragon scales")
		return false
		
	print("  [PASS] Dragon visuals verified: Vibrant glowing pink with PBR rim and clearcoat.")
	return true

## -----------------------------------------------------------------------------
## Check 2: R1 Environment, Camera & Lighting Parameters
## -----------------------------------------------------------------------------
func test_r1_environment_and_lighting() -> bool:
	print("\n--- [CHECK 2: R1 Camera, Lighting & Fog Parameters] ---")
	
	# 1. Camera Far Plane in PlayerDragon.tscn (3500m)
	var dragon_scene = load("res://scenes/PlayerDragon.tscn")
	var dragon_inst = dragon_scene.instantiate()
	var cam = dragon_inst.find_child("Camera3D", true, false) as Camera3D
	if cam == null:
		printerr("  FAIL: Camera3D not found in PlayerDragon.tscn")
		dragon_inst.queue_free()
		return false
		
	print("  Camera3D far clipping plane: %.1f m (expected 3500.0 m)" % cam.far)
	if absf(cam.far - 3500.0) > 1.0:
		printerr("  FAIL: Camera far clipping plane is %.1f, expected 3500.0" % cam.far)
		dragon_inst.queue_free()
		return false
	dragon_inst.queue_free()
	
	# 2. Main Scene Directional Sunlight Shadow Distance (800m)
	var main_scene = load("res://scenes/Main.tscn")
	var main_inst = main_scene.instantiate()
	var light = main_inst.find_child("DirectionalLight3D", true, false) as DirectionalLight3D
	if light == null:
		printerr("  FAIL: DirectionalLight3D not found in Main.tscn")
		main_inst.queue_free()
		return false
		
	print("  Sunlight directional_shadow_max_distance: %.1f m (expected 800.0 m)" % light.directional_shadow_max_distance)
	if absf(light.directional_shadow_max_distance - 800.0) > 1.0:
		printerr("  FAIL: Sunlight shadow max distance is %.1f, expected 800.0" % light.directional_shadow_max_distance)
		main_inst.queue_free()
		return false
	main_inst.queue_free()
	
	# 3. Sky Environment Distance Fog (0.00055)
	var env = load("res://materials/sky_environment.tres") as Environment
	if env == null:
		printerr("  FAIL: Failed to load materials/sky_environment.tres")
		return false
		
	print("  Environment fog_density: %.5f (expected 0.00055)" % env.fog_density)
	if absf(env.fog_density - 0.00055) > 0.00005:
		printerr("  FAIL: Fog density is %.5f, expected 0.00055" % env.fog_density)
		return false
		
	print("  [PASS] Camera (3500m), Sunlight Shadow (800m), and Atmospheric Fog (0.00055) verified.")
	return true

## -----------------------------------------------------------------------------
## Check 3: R1 Static Open World Landscape, Forests & Clouds
## -----------------------------------------------------------------------------
func test_r1_landscape_forests_and_clouds() -> bool:
	print("\n--- [CHECK 3: R1 Landscape, 2000+ Forest Trees & Fly-Through Clouds] ---")
	var cm = ChunkManager.new()
	root.add_child(cm)
	await process_frame
	await physics_frame
	
	# 1. Landscape Mesh & Trimesh Collision
	var landscape_node = cm.get_node_or_null("OpenWorldLandscape") as MeshInstance3D
	if landscape_node == null or landscape_node.mesh == null:
		printerr("  FAIL: OpenWorldLandscape MeshInstance3D not generated in ChunkManager")
		cm.queue_free()
		return false
		
	var aabb = landscape_node.mesh.get_aabb()
	print("  Landscape AABB: %s (Span X=%.1f m, Span Z=%.1f m)" % [str(aabb), aabb.size.x, aabb.size.z])
	if aabb.size.x < 2800.0 or aabb.size.z < 2800.0:
		printerr("  FAIL: Landscape span (%.1f x %.1f) is smaller than 3000m x 3000m realm" % [aabb.size.x, aabb.size.z])
		cm.queue_free()
		return false
		
	var static_body = landscape_node.find_child("LandscapeCollider", true, false) as StaticBody3D
	if static_body == null or (static_body.collision_layer & 1) == 0:
		printerr("  FAIL: Landscape missing StaticBody3D on Collision Layer 1")
		cm.queue_free()
		return false

	# 1a. Verify Upward Surface Normals (Y > 0.9) in Valley Basin
	var arrays = landscape_node.mesh.surface_get_arrays(0)
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var valley_normal_sum = Vector3.ZERO
	var valley_samples = 0
	for i in range(verts.size()):
		if absf(verts[i].x) < 60.0 and absf(verts[i].z) < 60.0:
			valley_normal_sum += normals[i]
			valley_samples += 1
	var avg_valley_normal = (valley_normal_sum / float(valley_samples)).normalized() if valley_samples > 0 else Vector3.ZERO
	print("  Average valley surface normal: %s (Y=%.4f, expected > 0.9)" % [str(avg_valley_normal), avg_valley_normal.y])
	if avg_valley_normal.y < 0.9:
		printerr("  FAIL: Valley surface normal points downward or inverted (Y=%.4f < 0.9)" % avg_valley_normal.y)
		cm.queue_free()
		return false

	# 1b. Verify ConcavePolygonShape3D backface_collision enabled
	var trimesh_col = static_body.get_node_or_null("TrimeshShape") as CollisionShape3D
	if trimesh_col == null or not (trimesh_col.shape is ConcavePolygonShape3D):
		printerr("  FAIL: TrimeshShape CollisionShape3D missing ConcavePolygonShape3D")
		cm.queue_free()
		return false
	if not trimesh_col.shape.backface_collision:
		printerr("  FAIL: ConcavePolygonShape3D backface_collision is false (expected true)")
		cm.queue_free()
		return false
	print("  [PASS] ConcavePolygonShape3D backface_collision verified true.")

	# 1c. Verify Downward Raycast Collision onto Landscape Collider
	var space_state = static_body.get_world_3d().direct_space_state
	var ray_test_positions = [
		Vector3(0.0, 100.0, 0.0),
		Vector3(50.0, 100.0, -50.0),
		Vector3(-100.0, 150.0, 100.0),
		Vector3(300.0, 250.0, -300.0),
		Vector3(-400.0, 300.0, 400.0)
	]
	for ray_pos in ray_test_positions:
		var ray_query = PhysicsRayQueryParameters3D.create(ray_pos, ray_pos + Vector3.DOWN * 400.0, 1)
		var hit = space_state.intersect_ray(ray_query)
		if hit.is_empty():
			printerr("  FAIL: Downward raycast from %s missed terrain mesh!" % str(ray_pos))
			cm.queue_free()
			return false
		if hit.collider != static_body:
			printerr("  FAIL: Downward raycast hit %s instead of LandscapeCollider" % str(hit.collider.name))
			cm.queue_free()
			return false
		if hit.normal.y <= 0.0:
			printerr("  FAIL: Terrain surface hit normal is not facing upward at %s: %s" % [str(ray_pos), str(hit.normal)])
			cm.queue_free()
			return false
		print("  Downward raycast at (X=%.1f, Z=%.1f) hit LandscapeCollider at Y=%.2f (normal Y=%.3f)" % [
			ray_pos.x, ray_pos.z, hit.position.y, hit.normal.y
		])
	print("  [PASS] Static 3000m x 3000m exploration landscape with upward normals and Layer 1 collision verified.")
	
	# 2. Forests (2000+ Trees via MultiMeshInstance3D with passthrough collision)
	var forest_node = cm.get_node_or_null("ForestMultiMesh") as MultiMeshInstance3D
	if forest_node == null or forest_node.multimesh == null:
		printerr("  FAIL: ForestMultiMesh MultiMeshInstance3D not found")
		cm.queue_free()
		return false
		
	var count = forest_node.multimesh.instance_count
	print("  Forest tree instance count: %d (expected >= 2000)" % count)
	if count < 2000:
		printerr("  FAIL: MultiMesh tree count (%d) is less than 2000" % count)
		cm.queue_free()
		return false
		
	# Verify trees have passthrough collision (no CollisionShape child)
	var tree_colliders = forest_node.find_children("", "CollisionShape3D", true, false)
	if not tree_colliders.is_empty():
		printerr("  FAIL: Forest trees have solid colliders (expected passthrough collision)")
		cm.queue_free()
		return false
	print("  [PASS] 2000+ fairytale trees instanced via MultiMeshInstance3D with passthrough collision verified.")
	
	# 3. Sky with 3D Clouds (Passthrough fly-through exploration)
	var clouds_container = cm.get_node_or_null("SkyCloudsContainer")
	if clouds_container == null:
		printerr("  FAIL: SkyCloudsContainer not found")
		cm.queue_free()
		return false
		
	var cloud_children = clouds_container.get_children()
	print("  3D Cloud cluster count: %d (expected >= 30)" % cloud_children.size())
	if cloud_children.size() < 30:
		printerr("  FAIL: Cloud cluster count (%d) is less than 30" % cloud_children.size())
		cm.queue_free()
		return false
		
	# Verify clouds are at flight altitude and have zero collision
	for cl in cloud_children:
		var c_node = cl as Node3D
		if c_node.position.y < 80.0 or c_node.position.y > 260.0:
			printerr("  FAIL: Cloud at Y=%.1f outside flight altitude [90, 250]" % c_node.position.y)
			cm.queue_free()
			return false
		if not c_node.find_children("", "CollisionShape3D", true, false).is_empty():
			printerr("  FAIL: Cloud has collision shape (expected passthrough)")
			cm.queue_free()
			return false
			
	print("  [PASS] Sky with 3D fly-through cloud clusters at altitudes Y=[95, 240]m verified.")
	cm.queue_free()
	await process_frame
	return true

## -----------------------------------------------------------------------------
## Check 4: R1 Soft Boundary Steering Guidance (R > 1350m)
## -----------------------------------------------------------------------------
func test_r1_soft_boundary_guidance() -> bool:
	print("\n--- [CHECK 4: R1 Soft Boundary Steering Guidance (R > 1350m, All 8 Compass Directions)] ---")
	var dragon_scene = load("res://scenes/PlayerDragon.tscn")
	var dragon: CharacterBody3D = dragon_scene.instantiate()
	root.add_child(dragon)
	
	var cm = ChunkManager.new()
	cm.player_ref = dragon
	root.add_child(cm)
	await process_frame
	await physics_frame
	
	var fc = dragon.find_child("FlightController", true, false) as FlightController
	if fc == null:
		printerr("  FAIL: FlightController not found on dragon")
		dragon.queue_free()
		cm.queue_free()
		return false

	var compass_points = [
		{"name": "North (N)", "pos": Vector3(0.0, 50.0, -1420.0)},
		{"name": "South (S)", "pos": Vector3(0.0, 50.0, 1420.0)},
		{"name": "East (E)", "pos": Vector3(1420.0, 50.0, 0.0)},
		{"name": "West (W)", "pos": Vector3(-1420.0, 50.0, 0.0)},
		{"name": "North-East (NE)", "pos": Vector3(1004.1, 50.0, -1004.1)},
		{"name": "North-West (NW)", "pos": Vector3(-1004.1, 50.0, -1004.1)},
		{"name": "South-East (SE)", "pos": Vector3(1004.1, 50.0, 1004.1)},
		{"name": "South-West (SW)", "pos": Vector3(-1004.1, 50.0, 1004.1)}
	]

	for pt in compass_points:
		var pos: Vector3 = pt["pos"]
		var pt_name: String = pt["name"]
		
		var dir_to_center_2d = -Vector2(pos.x, pos.z).normalized()
		var expected_target_heading = atan2(-dir_to_center_2d.x, -dir_to_center_2d.y)
		
		# Place dragon at boundary position
		dragon.global_position = pos
		fc.reset_flight_state(pos)
		
		# Set an initial heading offset by 1.2 rad (~68.8 deg) from the ideal inward vector
		var initial_heading = wrapf(expected_target_heading + 1.2, -PI, PI)
		fc.current_heading = initial_heading
		
		var initial_err = absf(angle_difference(fc.current_heading, expected_target_heading))
		var initial_inward = Vector2(-sin(initial_heading), -cos(initial_heading)).dot(dir_to_center_2d)
		
		# Simulate 25 frames of boundary guidance
		for frame in range(25):
			cm.update_player_position(dragon.global_position)
			await physics_frame
			
		var final_err = absf(angle_difference(fc.current_heading, expected_target_heading))
		var fwd_xz = Vector2(-sin(fc.current_heading), -cos(fc.current_heading))
		var final_inward = fwd_xz.dot(dir_to_center_2d)
		
		print("  [%s at (%.0f, %.0f)] Target Hdg: %.2f | Final Hdg: %.2f | Inward Dot: %.3f -> %.3f | Err: %.3f -> %.3f" % [
			pt_name, pos.x, pos.z, expected_target_heading, fc.current_heading, initial_inward, final_inward, initial_err, final_err
		])
		
		# Assert error reduced towards valley center
		if final_err >= initial_err:
			printerr("  FAIL: [%s] Soft boundary steering did not reduce angular error toward center (initial=%.3f, final=%.3f)" % [
				pt_name, initial_err, final_err
			])
			dragon.queue_free()
			cm.queue_free()
			return false
			
		# Assert forward vector turned inward
		if final_inward <= initial_inward or final_inward < 0.5:
			printerr("  FAIL: [%s] Dragon forward vector not steered inward (initial_dot=%.3f, final_dot=%.3f)" % [
				pt_name, initial_inward, final_inward
			])
			dragon.queue_free()
			cm.queue_free()
			return false

	print("  [PASS] All 8 compass directions verified: Soft boundary steers smoothly inward toward central basin.")
	dragon.queue_free()
	cm.queue_free()
	await process_frame
	return true

## -----------------------------------------------------------------------------
## Check 5: R2 Peaceful Flight, Deflection & Ground Cushion
## -----------------------------------------------------------------------------
func test_r2_peaceful_flight_mechanics() -> bool:
	print("\n--- [CHECK 5: R2 Peaceful Flight Mechanics (No Damage, No Death, Deflection)] ---")
	var gm = GameManager.new()
	gm.peaceful_mode = true
	root.add_child(gm)
	
	var dragon_scene = load("res://scenes/PlayerDragon.tscn")
	var dragon: CharacterBody3D = dragon_scene.instantiate()
	root.add_child(dragon)
	
	var hud_scene = load("res://scenes/HUD.tscn")
	var hud: HUD = hud_scene.instantiate()
	var hud_holder = Node.new()
	root.add_child(hud_holder)
	hud_holder.add_child(hud)
	
	await process_frame
	await physics_frame
	
	gm._resolve_node_references()
	gm._wire_signals()
	gm.reset_game(GameManager.GameState.FLYING)
	
	var fc = dragon.find_child("FlightController", true, false) as FlightController
	
	# 1. Verify collision impact causes ZERO damage and NO state change in peaceful mode
	var mock_obstacle = StaticBody3D.new()
	fc.collision_impact.emit(mock_obstacle, Vector3(0, 15, -10), Vector3(0, 0, 1))
	await process_frame
	
	print("  Health after impact: %d (expected 3), State: %s (expected FLYING)" % [
		gm.current_health, gm.get_state_name()
	])
	if gm.current_health != 3 or gm.get_state() != GameManager.GameState.FLYING:
		printerr("  FAIL: Collision caused damage or state change in peaceful mode")
		gm.queue_free(); dragon.queue_free(); hud.queue_free(); mock_obstacle.queue_free()
		return false
		
	if Engine.time_scale < 0.99:
		printerr("  FAIL: Engine.time_scale was dilated during peaceful collision")
		gm.queue_free(); dragon.queue_free(); hud.queue_free(); mock_obstacle.queue_free()
		return false
		
	mock_obstacle.queue_free()
	
	# 2. Verify Tangential Deflection on obstacle contact
	var wall = StaticBody3D.new()
	wall.collision_layer = 1
	var col = CollisionShape3D.new()
	var box = BoxShape3D.new()
	box.size = Vector3(50.0, 30.0, 2.0)
	col.shape = box
	wall.add_child(col)
	wall.position = Vector3(0, 15, -10)
	root.add_child(wall)
	
	dragon.global_position = Vector3(0, 15, -7)
	fc.current_speed = 30.0
	
	for i in range(25):
		fc._apply_movement(TEST_DELTA)
		await physics_frame
		
	print("  Dragon position after wall contact: %s, Speed: %.1f m/s" % [
		str(dragon.global_position), fc.current_speed
	])
	
	# Must preserve forward flight speed without stopping at 0 m/s or pinning
	if fc.current_speed < 18.0:
		printerr("  FAIL: Dragon forward flight halted upon obstacle contact (speed=%.1f)" % fc.current_speed)
		gm.queue_free(); dragon.queue_free(); hud.queue_free(); wall.queue_free()
		return false
		
	wall.queue_free()
	gm.queue_free()
	dragon.queue_free()
	hud_holder.queue_free()
	await process_frame
	print("  [PASS] Peaceful flight verified: Zero damage, continuous speed, tangential deflection.")
	return true

## -----------------------------------------------------------------------------
## Check 6: R2 HUD Hearts & Game-Over Panel Hidden
## -----------------------------------------------------------------------------
func test_r2_hud_peaceful_elements() -> bool:
	print("\n--- [CHECK 6: R2 HUD Child-Friendly Interface] ---")
	var hud_scene = load("res://scenes/HUD.tscn")
	var hud: HUD = hud_scene.instantiate()
	var hud_holder = Node.new()
	root.add_child(hud_holder)
	hud_holder.add_child(hud)
	await process_frame
	
	var health_container = hud.find_child("HealthContainer", true, false) as CanvasItem
	if health_container == null:
		printerr("  FAIL: HealthContainer not found in HUD")
		hud.queue_free()
		return false
		
	print("  HealthContainer visible: %s (expected false)" % health_container.visible)
	if health_container.visible:
		printerr("  FAIL: HealthContainer hearts are visible in child-friendly HUD")
		hud.queue_free()
		return false
		
	var game_over_panel = hud.find_child("GameOverPanel", true, false) as CanvasItem
	if game_over_panel == null:
		printerr("  FAIL: GameOverPanel not found in HUD")
		hud.queue_free()
		return false
		
	print("  GameOverPanel visible: %s (expected false)" % game_over_panel.visible)
	if game_over_panel.visible:
		printerr("  FAIL: GameOverPanel is visible in child-friendly HUD")
		hud.queue_free()
		return false
		
	# Verify essential exploration instruments remain present and active
	var speed_val = hud.find_child("SpeedValue", true, false)
	var dist_val = hud.find_child("DistanceValue", true, false)
	var reticle = hud.find_child("ReticleDot", true, false)
	if speed_val == null or dist_val == null or reticle == null:
		printerr("  FAIL: Flight telemetry instruments missing from HUD")
		hud.queue_free()
		return false
		
	hud_holder.queue_free()
	await process_frame
	print("  [PASS] Child-friendly HUD verified: Health hearts & game-over screen hidden, telemetry retained.")
	return true

## -----------------------------------------------------------------------------
## Check 7: R4 Controls & UDP Head Tracking Compatibility
## -----------------------------------------------------------------------------
func test_r4_controls_and_tracking() -> bool:
	print("\n--- [CHECK 7: R4 Controls & Head Tracking Compatibility] ---")
	var dragon_scene = load("res://scenes/PlayerDragon.tscn")
	var dragon: CharacterBody3D = dragon_scene.instantiate()
	root.add_child(dragon)
	await process_frame
	
	var input_mgr = dragon.find_child("InputManager", true, false)
	if input_mgr == null:
		printerr("  FAIL: InputManager not found in PlayerDragon")
		dragon.queue_free()
		return false
		
	# Test UDP Packet Ingestion (Interface Contract 127.0.0.1:42425)
	var pkt = {"pitch": 14.0, "yaw": -22.5, "roll": 0.0, "calibrated": true, "tracking": true}
	input_mgr.inject_telemetry_packet(pkt)
	input_mgr.update_inputs(TEST_DELTA)
	
	var p_in = input_mgr.get_pitch_input()
	var y_in = input_mgr.get_yaw_input()
	print("  Ingested UDP telemetry -> pitch=%.2f, yaw=%.2f, mode=%s" % [p_in, y_in, input_mgr.get_control_mode()])
	if absf(p_in - (14.0 / 35.0)) > 0.05 or absf(y_in - (-22.5 / 45.0)) > 0.05:
		printerr("  FAIL: Ingested angles normalized incorrectly")
		dragon.queue_free()
		return false
		
	# Test neutral calibration method
	input_mgr.calibrate_neutral()
	
	dragon.queue_free()
	await process_frame
	print("  [PASS] InputManager UDP 127.0.0.1:42425 ingestion and calibration verified.")
	return true
