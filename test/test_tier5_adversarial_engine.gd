extends SceneTree

# ==============================================================================
# test_tier5_adversarial_engine.gd - Tier 5 Adversarial Stress & Invariant Test Suite
# ==============================================================================
# Covers:
# - TEST-T5-ADV-01: Kinematic Extremes, Delta Resiliency & 100k Steps Basis Invariant
# - TEST-T5-ADV-02: Collision Stress, 54 m/s Zero-Tunneling & Multi-Collider Invariant
# - TEST-T5-ADV-03: Procedural Realm Boundary Seeds & 500-Cycle Zero Memory Leak Invariant
# - TEST-T5-ADV-04: Game Loop Determinism, Reset Spam & Hit-Stop Time Scale Invariant
# - TEST-T5-ADV-05: HUD Telemetry Robustness, Clamping & Boundary Value Display
# ==============================================================================

const FlightController = preload("res://scripts/FlightController.gd")
const CameraFollow = preload("res://scripts/CameraFollow.gd")
const InputManager = preload("res://scripts/InputManager.gd")
const GameManager = preload("res://scripts/GameManager.gd")
const ChunkManager = preload("res://scripts/ChunkManager.gd")
const ProceduralMeshGen = preload("res://scripts/ProceduralMeshGen.gd")
const HUD = preload("res://scripts/HUD.gd")

func _init() -> void:
	print("==================================================================")
	print("   TIER 5 ADVERSARIAL STRESS & ENGINE HARDENING TEST SUITE")
	print("==================================================================")
	
	var watchdog = create_timer(30.0)
	watchdog.timeout.connect(func():
		printerr("[FATAL] Tier 5 watchdog timeout exceeded. Aborting.")
		quit(1)
	)
	
	var passed = await run_adversarial_battery()
	if passed:
		print("\n==================================================================")
		print("   ALL TIER 5 ADVERSARIAL TESTS PASSED (Exit code 0)")
		print("==================================================================")
		quit(0)
	else:
		printerr("\n==================================================================")
		printerr("   TIER 5 ADVERSARIAL TESTS FAILED (Exit code 1)")
		printerr("==================================================================")
		quit(1)

func run_adversarial_battery() -> bool:
	var world = Node3D.new()
	root.add_child(world)
	await process_frame
	await physics_frame
	
	var all_passed = true
	all_passed = all_passed and await test_adv_01_kinematics(world)
	all_passed = all_passed and await test_adv_02_collision(world)
	all_passed = all_passed and await test_adv_03_procedural_memory(world)
	all_passed = all_passed and await test_adv_04_game_loop(world)
	all_passed = all_passed and await test_adv_05_hud(world)
	
	world.queue_free()
	await process_frame
	return all_passed

func test_adv_01_kinematics(parent: Node) -> bool:
	print("\n--- TEST-T5-ADV-01: Kinematics Extremes & 100k Steps Basis Invariant ---")
	var dragon_scene = load("res://scenes/PlayerDragon.tscn")
	var dragon: CharacterBody3D = dragon_scene.instantiate()
	parent.add_child(dragon)
	await process_frame
	await physics_frame
	
	var fc = dragon.find_child("FlightController", true, false)
	fc.reset_flight_state(Vector3(0, 15, 0))
	
	var min_det = 1.0
	var max_det = 1.0
	var non_finite = 0
	var rng = RandomNumberGenerator.new()
	rng.seed = 98765
	
	for i in range(100000):
		var p_in = sin(float(i) * 0.05) * rng.randf_range(0.5, 1.5)
		var y_in = cos(float(i) * 0.03) * rng.randf_range(0.5, 1.5)
		var r_in = sin(float(i) * 0.07) * rng.randf_range(0.5, 1.5)
		var dt = rng.randf_range(0.001, 0.05)
		
		fc._update_speed(clampf(p_in, -1.0, 1.0), dt)
		fc._update_attitude(clampf(p_in, -1.0, 1.0), clampf(y_in, -1.0, 1.0), clampf(r_in, -1.0, 1.0), dt)
		
		var det = dragon.global_transform.basis.determinant()
		if det < min_det: min_det = det
		if det > max_det: max_det = det
		if is_nan(det) or is_inf(det) or is_nan(fc.current_speed): non_finite += 1
		
	var det_ok = abs(min_det - 1.0) < 0.0001 and abs(max_det - 1.0) < 0.0001
	print("  100k steps det=[%f, %f], non_finite=%d (det_ok: %s)" % [min_det, max_det, non_finite, det_ok])
	
	# Extreme delta times
	fc._physics_process(0.0)
	fc._physics_process(-1.0)
	fc._update_speed(-1.0, 10.0)
	var speed_ok = (fc.current_speed <= 54.0)
	print("  Lag spike (10s) dive speed: %f (<= 54.0: %s)" % [fc.current_speed, speed_ok])
	
	dragon.queue_free()
	await process_frame
	return det_ok and non_finite == 0 and speed_ok

func test_adv_02_collision(parent: Node) -> bool:
	print("\n--- TEST-T5-ADV-02: Collision Stress, Tunneling & Multi-Collider Invariant ---")
	var gm = GameManager.new()
	gm.peaceful_mode = false
	parent.add_child(gm)
	
	var dragon_scene = load("res://scenes/PlayerDragon.tscn")
	var dragon: CharacterBody3D = dragon_scene.instantiate()
	parent.add_child(dragon)
	
	var hud_scene = load("res://scenes/HUD.tscn")
	var hud: HUD = hud_scene.instantiate()
	parent.add_child(hud)
	
	var wall = StaticBody3D.new()
	wall.collision_layer = 1
	var col = CollisionShape3D.new()
	var box = BoxShape3D.new()
	box.size = Vector3(100.0, 50.0, 1.0)
	col.shape = box
	wall.add_child(col)
	wall.position = Vector3(0, 15, -10)
	parent.add_child(wall)
	
	await process_frame
	await physics_frame
	
	gm._resolve_node_references()
	gm._wire_signals()
	gm.reset_game(GameManager.GameState.FLYING)
	
	var fc = dragon.find_child("FlightController", true, false)
	dragon.global_position = Vector3(0, 15, -7)
	fc.current_speed = 54.0
	
	for tick in range(30):
		fc._apply_movement(1.0 / 60.0)
		await physics_frame
		if gm.current_health < 3: break
		
	var zero_tunneling = (dragon.global_position.z > -9.5 and gm.current_health == 2)
	print("  Zero tunneling at 54 m/s: %s (stopped at Z = %f)" % [zero_tunneling, dragon.global_position.z])
	
	# Multi-collider same frame
	gm.is_invulnerable = false
	var wall2 = StaticBody3D.new()
	parent.add_child(wall2)
	wall2.collision_layer = 1
	fc.collision_impact.emit(wall, dragon.global_position, Vector3(0, 0, 1))
	fc.collision_impact.emit(wall2, dragon.global_position, Vector3(1, 0, 0))
	var multi_hit_ok = (gm.current_health == 1)
	print("  Multi-collider single decrement invariant: %s (health: %d)" % [multi_hit_ok, gm.current_health])
	
	gm.queue_free()
	dragon.queue_free()
	hud.queue_free()
	wall.queue_free()
	wall2.queue_free()
	await process_frame
	return zero_tunneling and multi_hit_ok

func test_adv_03_procedural_memory(parent: Node) -> bool:
	print("\n--- TEST-T5-ADV-03: Procedural Boundary Seeds & 500-Cycle Zero Leak Invariant ---")
	var seeds = [0, -1, 2147483647, -2147483648, 9223372036854775807, -9223372036854775808]
	var seeds_ok = true
	for s in seeds:
		var m = ProceduralMeshGen.generate_needle_spire(60.0, 7.0, s)
		if m.get_faces().size() == 0: seeds_ok = false
	print("  Extreme boundary seeds verified: %s" % seeds_ok)
	
	var cm = ChunkManager.new()
	parent.add_child(cm)
	cm.setup_corridor(null, 42)
	await process_frame
	await physics_frame
	
	for cycle in range(100): cm.recycle_rear_chunk()
	await process_frame
	var nodes_100 = Performance.get_monitor(Performance.OBJECT_NODE_COUNT)
	var objs_100 = Performance.get_monitor(Performance.OBJECT_COUNT)
	
	for cycle in range(400): cm.recycle_rear_chunk()
	await process_frame
	var nodes_500 = Performance.get_monitor(Performance.OBJECT_NODE_COUNT)
	var objs_500 = Performance.get_monitor(Performance.OBJECT_COUNT)
	
	var zero_leak = (nodes_500 == nodes_100 and objs_500 == objs_100)
	print("  Zero leak across 400 chunk recycles: %s (nodes: %d -> %d, objs: %d -> %d)" % [
		zero_leak, nodes_100, nodes_500, objs_100, objs_500
	])
	
	cm.queue_free()
	await process_frame
	return seeds_ok and zero_leak

func test_adv_04_game_loop(parent: Node) -> bool:
	print("\n--- TEST-T5-ADV-04: Game Loop Determinism & Hit-Stop Time Scale Invariant ---")
	var gm = GameManager.new()
	parent.add_child(gm)
	
	var dragon_scene = load("res://scenes/PlayerDragon.tscn")
	var dragon: CharacterBody3D = dragon_scene.instantiate()
	parent.add_child(dragon)
	
	await process_frame
	gm._resolve_node_references()
	gm._wire_signals()
	
	# Rapid reset spam
	for i in range(50): gm.reset_game(GameManager.GameState.FLYING)
	var reset_spam_ok = (gm.current_health == 3 and Engine.time_scale == 1.0 and gm.get_state_name() == "FLYING")
	print("  50x reset spam in single frame invariant: %s" % reset_spam_ok)
	
	# Hit-stop cancellation
	gm._trigger_crash()
	gm.reset_game(GameManager.GameState.FLYING)
	await create_timer(0.25, true, false, true).timeout
	var hit_stop_cancel_ok = (gm.get_state_name() == "FLYING" and Engine.time_scale == 1.0)
	print("  Hit-stop reset cancellation invariant: %s" % hit_stop_cancel_ok)
	
	gm.queue_free()
	dragon.queue_free()
	await process_frame
	return reset_spam_ok and hit_stop_cancel_ok

func test_adv_05_hud(parent: Node) -> bool:
	print("\n--- TEST-T5-ADV-05: HUD Telemetry Robustness & Boundary Display ---")
	var hud_scene = load("res://scenes/HUD.tscn")
	var hud: HUD = hud_scene.instantiate()
	parent.add_child(hud)
	await process_frame
	
	hud.update_speed(-100.0)
	var speed_ok = (hud.speed_value.text == "0.0 m/s")
	
	hud.update_distance(-500.0)
	var dist_ok = (hud.distance_value.text == "0 m")
	
	hud.update_health(-5)
	var health_underflow_ok = (hud.current_health == 0)
	hud.update_health(999)
	var health_overflow_ok = (hud.current_health == 3)
	
	hud.update_reticle(100.0, -100.0)
	var reticle_offset = hud.reticle_dot.position + (hud.reticle_dot.size * 0.5)
	var reticle_ok = (reticle_offset.length() <= 50.0001)
	
	print("  HUD clamping (speed: %s, dist: %s, health: %s, reticle: %s)" % [
		speed_ok, dist_ok, health_underflow_ok and health_overflow_ok, reticle_ok
	])
	
	hud.queue_free()
	await process_frame
	return speed_ok and dist_ok and health_underflow_ok and health_overflow_ok and reticle_ok
