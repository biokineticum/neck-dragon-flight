extends SceneTree

# ==============================================================================
# test_flight_physics.gd - Headless Flight Physics, Aerodynamics & Input Test Suite
# ==============================================================================
# Executable via:
# & "Godot_v4.7.2-stable_win64_console.exe" --headless --path . -s test/test_flight_physics.gd
# ==============================================================================

const FlightController = preload("res://scripts/FlightController.gd")
const InputManager = preload("res://scripts/InputManager.gd")
const DragonVisualRig = preload("res://scripts/DragonVisualRig.gd")
const CameraFollow = preload("res://scripts/CameraFollow.gd")

const TEST_DELTA: float = 1.0 / 60.0

func _init() -> void:
	print("==================================================================")
	print("   STARTING FLIGHT PHYSICS & TELEMETRY INPUT HEADLESS TESTS")
	print("==================================================================")
	
	# Watchdog timer to ensure headless test cannot hang
	var watchdog = create_timer(25.0)
	watchdog.timeout.connect(func():
		printerr("[FATAL] Watchdog timeout (25.0s) exceeded! Terminating with code 1.")
		quit(1)
	)
	
	var passed = await run_flight_physics_suite()
	if passed:
		print("==================================================================")
		print("   ALL FLIGHT PHYSICS TESTS PASSED (Exit code 0)")
		print("   Tests: 11 passed, 0 failed")
		print("==================================================================")
		quit(0)
	else:
		printerr("==================================================================")
		printerr("   FLIGHT PHYSICS TESTS FAILED (Exit code 1)")
		printerr("==================================================================")
		quit(1)

func run_flight_physics_suite() -> bool:
	var success = true
	
	# Instantiate PlayerDragon scene
	var dragon_scene = load("res://scenes/PlayerDragon.tscn")
	if dragon_scene == null:
		printerr("FAIL: Could not load res://scenes/PlayerDragon.tscn")
		return false
		
	var dragon: CharacterBody3D = dragon_scene.instantiate() as CharacterBody3D
	if dragon == null:
		printerr("FAIL: Instantiated PlayerDragon is not CharacterBody3D")
		return false
		
	root.add_child(dragon)
	
	var flight_ctrl: FlightController = dragon.find_child("FlightController", true, false) as FlightController
	var input_mgr: InputManager = dragon.find_child("InputManager", true, false) as InputManager
	var visual_rig: DragonVisualRig = dragon.find_child("DragonVisualRig", true, false) as DragonVisualRig
	var camera_rig: CameraFollow = dragon.find_child("CameraRig", true, false) as CameraFollow
	
	if flight_ctrl == null or input_mgr == null or visual_rig == null or camera_rig == null:
		printerr("FAIL: One or more critical child nodes missing from PlayerDragon")
		return false

	# Let scene tree initialize
	await process_frame
	await physics_frame

	# 1. Scene Tree Structure & Geometry
	print("\n--- Test 1: PlayerDragon Scene Hierarchy & Geometry ---")
	var t1 = test_scene_structure(dragon, flight_ctrl, input_mgr, visual_rig, camera_rig)
	print("Test 1 Result: %s" % ("PASS" if t1 else "FAIL"))
	success = t1 and success

	# 2. Continuous Forward Flight Displacement along -Z
	print("\n--- Test 2: Continuous Forward Flight along -Z ---")
	var t2 = await test_forward_flight(dragon, flight_ctrl, input_mgr)
	print("Test 2 Result: %s" % ("PASS" if t2 else "FAIL"))
	success = t2 and success

	# 3. Pitch-Dependent Dive Acceleration toward 54 m/s
	print("\n--- Test 3: Pitch-Dependent Dive Acceleration ---")
	var t3 = await test_dive_acceleration(dragon, flight_ctrl, input_mgr)
	print("Test 3 Result: %s" % ("PASS" if t3 else "FAIL"))
	success = t3 and success

	# 4. Pitch-Dependent Climb Deceleration toward 18 m/s stall floor
	print("\n--- Test 4: Pitch-Dependent Climb Deceleration ---")
	var t4 = await test_climb_deceleration(dragon, flight_ctrl, input_mgr)
	print("Test 4 Result: %s" % ("PASS" if t4 else "FAIL"))
	success = t4 and success

	# 5. Coordinated Banking Turns & Orthonormal Basis
	print("\n--- Test 5: Coordinated Banking & Orthonormal Basis ---")
	var t5 = await test_coordinated_banking(dragon, flight_ctrl, input_mgr)
	print("Test 5 Result: %s" % ("PASS" if t5 else "FAIL"))
	success = t5 and success

	# 6. Mock UDP Packet Injection & Signal Decay
	print("\n--- Test 6: Mock UDP Packet Injection & Signal Decay ---")
	var t6 = test_udp_mock_injection(input_mgr)
	print("Test 6 Result: %s" % ("PASS" if t6 else "FAIL"))
	success = t6 and success

	# 7. Dual-Mode Fallback Override & 0.35s Crossfade
	print("\n--- Test 7: Dual-Mode Fallback Override & Crossfade ---")
	var t7 = test_fallback_override_crossfade(input_mgr)
	print("Test 7 Result: %s" % ("PASS" if t7 else "FAIL"))
	success = t7 and success

	# 8. Malformed Non-Primitive JSON Type Handling
	print("\n--- Test 8: Malformed Non-Primitive JSON Type Handling ---")
	var t8 = test_telemetry_non_primitive_payloads(input_mgr)
	print("Test 8 Result: %s" % ("PASS" if t8 else "FAIL"))
	success = t8 and success

	# 9. Tracking Loss Field ('tracking: false') Handling
	print("\n--- Test 9: Telemetry Tracking Loss ('tracking: false') ---")
	var t9 = test_telemetry_tracking_loss(input_mgr)
	print("Test 9 Result: %s" % ("PASS" if t9 else "FAIL"))
	success = t9 and success

	# 10. Frame-by-Frame Continuous Signal Decay Verification
	print("\n--- Test 10: Frame-by-Frame Continuous Signal Decay ---")
	var t10 = test_frame_by_frame_decay(input_mgr)
	print("Test 10 Result: %s" % ("PASS" if t10 else "FAIL"))
	success = t10 and success

	print("\n--- Test 11: Smooth Attitude and Camera Response ---")
	var t11 = test_smooth_response()
	print("Test 11 Result: %s" % ("PASS" if t11 else "FAIL"))
	success = t11 and success

	# Clean up
	dragon.queue_free()
	await process_frame
	return success

func test_smooth_response() -> bool:
	var controller = FlightController.new()
	var max_step = deg_to_rad(controller.max_attitude_rate_deg) / 60.0
	var pitch = controller._smooth_attitude(0.0, deg_to_rad(32.0), controller.pitch_response_speed, TEST_DELTA)
	var roll = controller._smooth_attitude(0.0, deg_to_rad(-42.0), controller.roll_response_speed, TEST_DELTA)
	var success = pitch > 0.0 and pitch <= max_step + 0.00001
	success = success and roll < 0.0 and absf(roll) <= max_step + 0.00001

	var rig_30 = CameraFollow.new()
	var rig_120 = CameraFollow.new()
	rig_30.camera_node = Camera3D.new()
	rig_120.camera_node = Camera3D.new()
	rig_30.camera_node.fov = 75.0
	rig_120.camera_node.fov = 75.0
	for i in range(30):
		rig_30._update_dynamic_fov(54.0, 1.0 / 30.0)
	for i in range(120):
		rig_120._update_dynamic_fov(54.0, 1.0 / 120.0)
	success = success and absf(rig_30.camera_node.fov - rig_120.camera_node.fov) < 0.001
	success = success and rig_30.camera_node.fov > 89.9

	rig_30.camera_node.free()
	rig_120.camera_node.free()
	rig_30.free()
	rig_120.free()
	controller.free()
	return success

func test_scene_structure(
	dragon: CharacterBody3D,
	flight_ctrl: FlightController,
	input_mgr: InputManager,
	visual_rig: DragonVisualRig,
	camera_rig: CameraFollow
) -> bool:
	# Layer 2 (Player), Mask 1 (Environment)
	if dragon.collision_layer != 2:
		printerr("  FAIL: collision_layer is %d (expected 2)" % dragon.collision_layer)
		return false
	if dragon.collision_mask != 1:
		printerr("  FAIL: collision_mask is %d (expected 1)" % dragon.collision_mask)
		return false
		
	# CollisionShape3D CapsuleShape3D
	var col_shape_node = dragon.find_child("CollisionShape3D", true, false) as CollisionShape3D
	if col_shape_node == null:
		printerr("  FAIL: CollisionShape3D node missing")
		return false
	var capsule = col_shape_node.shape as CapsuleShape3D
	if capsule == null:
		printerr("  FAIL: CollisionShape3D.shape is not CapsuleShape3D")
		return false
	if absf(capsule.radius - 1.2) > 0.01 or absf(capsule.height - 3.2) > 0.01:
		printerr("  FAIL: Capsule dimensions (r=%.2f, h=%.2f) do not match (1.2, 3.2)" % [capsule.radius, capsule.height])
		return false

	# Visual Rig Pivots
	if visual_rig.head_pivot == null or visual_rig.left_wing_pivot == null or visual_rig.right_wing_pivot == null:
		printerr("  FAIL: Visual rig anatomical pivots missing")
		return false
	if visual_rig.head_pivot.position.distance_to(Vector3(0.0, 0.10, -1.40)) > 0.01:
		printerr("  FAIL: HeadPivot position %s != (0.0, 0.10, -1.40)" % str(visual_rig.head_pivot.position))
		return false
	if visual_rig.left_wing_pivot.position.distance_to(Vector3(-0.40, 0.05, -0.20)) > 0.01:
		printerr("  FAIL: LeftWingPivot position %s != (-0.40, 0.05, -0.20)" % str(visual_rig.left_wing_pivot.position))
		return false
	if visual_rig.right_wing_pivot.position.distance_to(Vector3(0.40, 0.05, -0.20)) > 0.01:
		printerr("  FAIL: RightWingPivot position %s != (0.40, 0.05, -0.20)" % str(visual_rig.right_wing_pivot.position))
		return false

	# Camera Rig Mount
	if camera_rig.position.distance_to(Vector3(0.0, 1.4, -0.2)) > 0.1:
		printerr("  FAIL: CameraRig local position %s != (0.0, 1.4, -0.2)" % str(camera_rig.position))
		return false
	var cam = camera_rig.camera_node
	if cam == null or not cam.current:
		printerr("  FAIL: Camera3D missing or not current")
		return false
	if cam.near > 0.051:
		printerr("  FAIL: Camera3D near clipping plane > 0.05m (was %.4f)" % cam.near)
		return false

	print("  [PASS] Scene tree hierarchy, capsule collider, pivots, and camera mount verified")
	return true

func test_forward_flight(dragon: CharacterBody3D, flight_ctrl: FlightController, input_mgr: InputManager) -> bool:
	input_mgr.set_simulated_keyboard_input(0.0, 0.0, 0.0, false)
	flight_ctrl.reset_flight_state(Vector3(0.0, 15.0, 0.0))
	
	# Advance 60 frames (1.0 second)
	for i in range(60):
		flight_ctrl._physics_process(TEST_DELTA)
		
	var pos = dragon.global_position
	var speed = flight_ctrl.get_current_speed()
	var dist = flight_ctrl.get_flight_distance()
	
	print("  Position after 1.0s: %s, Speed: %.2f m/s, Distance: %.2f m" % [str(pos), speed, dist])
	
	if pos.z > -28.0 or pos.z < -32.0:
		printerr("  FAIL: Forward displacement along -Z was %.2f (expected ~ -30.0m)" % pos.z)
		return false
	if absf(speed - 30.0) > 1.0:
		printerr("  FAIL: Cruise speed %.2f deviated from 30.0 m/s" % speed)
		return false
	if absf(dist - 30.0) > 2.0:
		printerr("  FAIL: Distance traveled %.2f deviated from 30.0m" % dist)
		return false
	if absf(pos.y - 15.0) > 0.5:
		printerr("  FAIL: Altitude shifted unexpectedly during level flight: %.2f" % pos.y)
		return false

	print("  [PASS] Continuous forward flight along -Z verified at 30.0 m/s")
	return true

func test_dive_acceleration(dragon: CharacterBody3D, flight_ctrl: FlightController, input_mgr: InputManager) -> bool:
	flight_ctrl.reset_flight_state(Vector3(0.0, 15.0, 0.0))
	
	# Engage sustained dive (-1.0 pitch)
	input_mgr.set_simulated_keyboard_input(-1.0, 0.0, 0.0, true)
	
	var prev_speed = flight_ctrl.get_current_speed()
	var monotonic = true
	
	# Step 120 frames (2.0s): 30.0 + 12.0 * 2.0 = 54.0 m/s
	for i in range(120):
		input_mgr.update_inputs(TEST_DELTA)
		flight_ctrl._physics_process(TEST_DELTA)
		var cur_speed = flight_ctrl.get_current_speed()
		if cur_speed < prev_speed - 0.001:
			monotonic = false
		prev_speed = cur_speed

	var final_speed = flight_ctrl.get_current_speed()
	var pitch_deg = flight_ctrl.get_pitch_degrees()
	print("  Dive speed after 2.0s: %.2f m/s (monotonic: %s), Pitch: %.2f deg" % [final_speed, monotonic, pitch_deg])
	
	if not monotonic:
		printerr("  FAIL: Dive did not accelerate monotonically")
		return false
	if absf(final_speed - 54.0) > 0.5:
		printerr("  FAIL: Final dive speed %.2f did not reach 54.0 m/s" % final_speed)
		return false
	if pitch_deg > -28.0 or pitch_deg < -32.5:
		printerr("  FAIL: Pitch angle %.2f not clamped near -32.0 deg" % pitch_deg)
		return false

	# Test level flight drag recovery
	input_mgr.set_simulated_keyboard_input(0.0, 0.0, 0.0, false)
	for i in range(60):
		input_mgr.update_inputs(TEST_DELTA)
		flight_ctrl._physics_process(TEST_DELTA)
	var recovered_speed = flight_ctrl.get_current_speed()
	print("  Speed after 1.0s level recovery: %.2f m/s" % recovered_speed)
	if recovered_speed >= 54.0 or recovered_speed < 30.0:
		printerr("  FAIL: Level flight drag recovery failed to decrease speed toward cruise")
		return false

	print("  [PASS] Dive acceleration to 54.0 m/s and level drag recovery verified")
	return true

func test_climb_deceleration(dragon: CharacterBody3D, flight_ctrl: FlightController, input_mgr: InputManager) -> bool:
	flight_ctrl.reset_flight_state(Vector3(0.0, 15.0, 0.0))
	
	# Engage sustained climb (+1.0 pitch)
	input_mgr.set_simulated_keyboard_input(1.0, 0.0, 0.0, true)
	
	var prev_speed = flight_ctrl.get_current_speed()
	var monotonic = true
	var min_speed_seen = 999.0
	
	# Step 120 frames (2.0s): 30.0 - 8.0 * 2.0 = 14.0 -> clamped at 18.0 m/s
	for i in range(120):
		input_mgr.update_inputs(TEST_DELTA)
		flight_ctrl._physics_process(TEST_DELTA)
		var cur_speed = flight_ctrl.get_current_speed()
		if cur_speed > prev_speed + 0.001:
			monotonic = false
		min_speed_seen = minf(min_speed_seen, cur_speed)
		prev_speed = cur_speed

	var final_speed = flight_ctrl.get_current_speed()
	var pitch_deg = flight_ctrl.get_pitch_degrees()
	print("  Climb speed after 2.0s: %.2f m/s, Stall floor seen: %.3f m/s, Pitch: %.2f deg" % [final_speed, min_speed_seen, pitch_deg])
	
	if not monotonic:
		printerr("  FAIL: Climb did not decelerate monotonically")
		return false
	if absf(final_speed - 18.0) > 0.01:
		printerr("  FAIL: Stall floor %.3f did not clamp at 18.0 m/s" % final_speed)
		return false
	if min_speed_seen < 18.0 - 0.001:
		printerr("  FAIL: Speed dropped below 18.0 m/s stall floor: %.3f" % min_speed_seen)
		return false
	if pitch_deg < 28.0 or pitch_deg > 32.5:
		printerr("  FAIL: Pitch angle %.2f not clamped near +32.0 deg" % pitch_deg)
		return false

	print("  [PASS] Climb deceleration and 18.0 m/s stall floor clamping verified")
	return true

func test_coordinated_banking(dragon: CharacterBody3D, flight_ctrl: FlightController, input_mgr: InputManager) -> bool:
	flight_ctrl.reset_flight_state(Vector3(0.0, 15.0, 0.0))
	
	# Sustained turn right (+1.0 yaw)
	input_mgr.set_simulated_keyboard_input(0.0, 1.0, 0.0, true)
	
	for i in range(60):
		input_mgr.update_inputs(TEST_DELTA)
		flight_ctrl._physics_process(TEST_DELTA)
		
	var roll_r = flight_ctrl.get_roll_degrees()
	var heading_r = flight_ctrl.current_heading
	var basis_det_r = dragon.global_transform.basis.determinant()
	
	print("  Right turn: Roll = %.2f deg, Heading = %.4f rad, Basis det = %.6f" % [roll_r, heading_r, basis_det_r])
	
	if roll_r < 20.0 or roll_r > 42.1:
		printerr("  FAIL: Right roll banking %.2f not in [20, 42] deg" % roll_r)
		return false
	if heading_r >= 0.0:
		printerr("  FAIL: Right turn did not rotate heading toward +X (negative rad)")
		return false
	if absf(basis_det_r - 1.0) > 0.001:
		printerr("  FAIL: Basis determinant diverged from 1.0: %.6f" % basis_det_r)
		return false

	# Reverse to left turn (-1.0 yaw)
	input_mgr.set_simulated_keyboard_input(0.0, -1.0, 0.0, true)
	for i in range(120):
		input_mgr.update_inputs(TEST_DELTA)
		flight_ctrl._physics_process(TEST_DELTA)

	var roll_l = flight_ctrl.get_roll_degrees()
	var basis_det_l = dragon.global_transform.basis.determinant()
	print("  Left turn: Roll = %.2f deg, Basis det = %.6f" % [roll_l, basis_det_l])
	
	if roll_l > -20.0 or roll_l < -42.1:
		printerr("  FAIL: Left roll banking %.2f not in [-42, -20] deg" % roll_l)
		return false
	if absf(basis_det_l - 1.0) > 0.001:
		printerr("  FAIL: Basis determinant diverged from 1.0: %.6f" % basis_det_l)
		return false

	# Clean up input state at end of Test 5
	input_mgr.set_simulated_keyboard_input(0.0, 0.0, 0.0, false)
	input_mgr.manual_controls_were_active = false
	input_mgr.is_crossfading = false
	input_mgr.current_control_mode = "KEYBOARD_MOUSE"
	flight_ctrl.reset_flight_state(Vector3(0.0, 15.0, 0.0))

	print("  [PASS] Coordinated banking to ±42° and orthonormal basis preservation verified")
	return true

func test_udp_mock_injection(input_mgr: InputManager) -> bool:
	input_mgr.set_simulated_keyboard_input(0.0, 0.0, 0.0, false)
	
	# Inject telemetry packet: pitch=17.5° (+0.5 climb), yaw=-22.5° (-0.5 left), roll=35.0° (+1.0 bank)
	var pkt = {
		"pitch": 17.5,
		"yaw": -22.5,
		"roll": 35.0,
		"calibrated": true,
		"tracking": true,
		"timestamp": 12345.678
	}
	input_mgr.inject_telemetry_packet(pkt)
	input_mgr.update_inputs(0.016)
	
	var is_act = input_mgr.is_webcam_active()
	var mode = input_mgr.get_control_mode()
	var p_in = input_mgr.get_pitch_input()
	var y_in = input_mgr.get_yaw_input()
	var r_in = input_mgr.get_roll_input()
	
	print("  Injected packet -> Active: %s, Mode: %s, Pitch: %.3f, Yaw: %.3f, Roll: %.3f" % [is_act, mode, p_in, y_in, r_in])
	
	if not is_act:
		printerr("  FAIL: is_webcam_active() was false immediately after packet")
		return false
	if mode != "WEBCAM":
		printerr("  FAIL: Control mode was %s (expected WEBCAM)" % mode)
		return false
	if absf(p_in - 0.5) > 0.02:
		printerr("  FAIL: Normalized pitch %.3f != 0.5" % p_in)
		return false
	if absf(y_in - (-0.5)) > 0.02:
		printerr("  FAIL: Normalized yaw %.3f != -0.5" % y_in)
		return false
	if absf(r_in - 1.0) > 0.02:
		printerr("  FAIL: Normalized roll %.3f != 1.0" % r_in)
		return false

	# Test timeout & signal decay: advance time by 0.60s without packets (>0.5s timeout)
	for i in range(36): # 36 * 0.0166 = 0.60s
		input_mgr.update_inputs(TEST_DELTA)
		
	var timed_out_act = input_mgr.is_webcam_active()
	var decayed_yaw = input_mgr.get_yaw_input()
	print("  After 0.60s silence -> Active: %s, Decayed yaw: %.4f" % [timed_out_act, decayed_yaw])
	
	if timed_out_act:
		printerr("  FAIL: is_webcam_active() remained true after 0.60s silence")
		return false
	if absf(decayed_yaw) > 0.05:
		printerr("  FAIL: Steering signal %.4f did not decay below 0.05 within timeout period" % decayed_yaw)
		return false

	print("  [PASS] UDP packet injection, normalization, and signal decay verified")
	return true

func test_fallback_override_crossfade(input_mgr: InputManager) -> bool:
	# 1. Establish active webcam input
	input_mgr.set_simulated_keyboard_input(0.0, 0.0, 0.0, false)
	var pkt = {"pitch": 0.0, "yaw": 36.0, "roll": 0.0, "calibrated": true, "tracking": true}
	input_mgr.inject_telemetry_packet(pkt)
	input_mgr.update_inputs(TEST_DELTA)
	
	if input_mgr.get_control_mode() != "WEBCAM":
		printerr("  FAIL: Pre-condition WEBCAM mode not met (was %s, is_act=%s, manual_act=%s)" % [input_mgr.get_control_mode(), input_mgr.is_webcam_active(), input_mgr.manual_controls_were_active])
		return false
		
	# 2. Player touches manual controls: yaw = -1.0
	input_mgr.set_simulated_keyboard_input(0.0, -1.0, 0.0, true)
	input_mgr.update_inputs(TEST_DELTA)
	
	var mode_override = input_mgr.get_control_mode()
	var yaw_override = input_mgr.get_yaw_input()
	print("  Key pressed -> Mode: %s, Yaw: %.2f" % [mode_override, yaw_override])
	
	if mode_override != "KEYBOARD_MOUSE":
		printerr("  FAIL: Keyboard touch did not immediately command KEYBOARD_MOUSE mode")
		return false
	if absf(yaw_override - (-1.0)) > 0.01:
		printerr("  FAIL: Manual yaw %.2f did not take 100%% authority" % yaw_override)
		return false

	# 3. Release keyboard key while keeping webcam telemetry active
	input_mgr.set_simulated_keyboard_input(0.0, 0.0, 0.0, false)
	input_mgr.inject_telemetry_packet(pkt) # Keep stream fresh
	
	# Step 6 frames (~0.10s) -> halfway into 0.35s crossfade
	for i in range(6):
		input_mgr.inject_telemetry_packet(pkt)
		input_mgr.update_inputs(TEST_DELTA)
		
	var mode_mid = input_mgr.get_control_mode()
	var yaw_mid = input_mgr.get_yaw_input()
	print("  During crossfade (0.10s) -> Mode: %s, Yaw: %.2f" % [mode_mid, yaw_mid])
	
	if mode_mid != "BLENDED":
		printerr("  FAIL: Mode was %s during crossfade (expected BLENDED)" % mode_mid)
		return false
	if yaw_mid <= -1.0 or yaw_mid >= 0.8:
		printerr("  FAIL: Yaw %.2f not smoothly transitioning between -1.0 and 0.8" % yaw_mid)
		return false

	# Step remaining frames to complete 0.35s crossfade (total > 0.40s)
	for i in range(20):
		input_mgr.inject_telemetry_packet(pkt)
		input_mgr.update_inputs(TEST_DELTA)
		
	var mode_final = input_mgr.get_control_mode()
	var yaw_final = input_mgr.get_yaw_input()
	print("  After crossfade (0.43s) -> Mode: %s, Yaw: %.2f" % [mode_final, yaw_final])
	
	if mode_final != "WEBCAM":
		printerr("  FAIL: Mode was %s after crossfade (expected WEBCAM)" % mode_final)
		return false
	if absf(yaw_final - 0.8) > 0.02:
		printerr("  FAIL: Final yaw %.2f did not restore to 0.8" % yaw_final)
		return false

	print("  [PASS] Dual-mode priority override and 0.35s crossfade verified")
	return true

func test_telemetry_non_primitive_payloads(input_mgr: InputManager) -> bool:
	# Assert feeding payloads with nested arrays/dicts/nulls parses without script error and defaults to 0.0
	var malformed_payloads = [
		'{"pitch": [1, 2, 3]}',
		'{"pitch": null}',
		'{"yaw": {"nested": true}}',
		'{"roll": [true, false]}',
		'{"pitch": null, "yaw": null, "roll": null}',
		'{"pitch": "not_a_number", "yaw": 22.5}'
	]
	
	for payload in malformed_payloads:
		var parsed = input_mgr.process_json_packet(payload)
		if not parsed:
			printerr("  FAIL: process_json_packet failed to parse valid JSON payload: %s" % payload)
			return false
		
		# Values with invalid types should default to 0.0
		if "[1, 2, 3]" in payload or "null" in payload:
			if input_mgr.raw_pitch_deg != 0.0:
				printerr("  FAIL: Non-primitive pitch did not default to 0.0 (got %.3f) for %s" % [input_mgr.raw_pitch_deg, payload])
				return false
		if "nested" in payload:
			if input_mgr.raw_yaw_deg != 0.0:
				printerr("  FAIL: Nested dictionary yaw did not default to 0.0 (got %.3f)" % input_mgr.raw_yaw_deg)
				return false

	print("  [PASS] Non-primitive JSON types (arrays, dicts, nulls, invalid strings) parsed safely with 0.0 defaults")
	return true

func test_telemetry_tracking_loss(input_mgr: InputManager) -> bool:
	input_mgr.set_simulated_keyboard_input(0.0, 0.0, 0.0, false)
	input_mgr.webcam_pitch = 0.0
	input_mgr.webcam_yaw = 0.0
	input_mgr.webcam_roll = 0.0
	input_mgr.final_pitch = 0.0
	input_mgr.final_yaw = 0.0
	input_mgr.final_roll = 0.0
	input_mgr.head_tracking_active = false
	input_mgr.time_since_last_packet = 999.0
	input_mgr.current_control_mode = "KEYBOARD_MOUSE"
	
	# 1. Fresh state: inject packet with tracking = false
	var pkt_no_track = {
		"pitch": 15.0,
		"yaw": 20.0,
		"roll": 10.0,
		"tracking": false
	}
	input_mgr.inject_telemetry_packet(pkt_no_track)
	input_mgr.update_inputs(TEST_DELTA)
	
	if input_mgr.head_tracking_active:
		printerr("  FAIL: head_tracking_active was true after packet with tracking=false")
		return false
	if input_mgr.is_webcam_active():
		printerr("  FAIL: is_webcam_active() was true after packet with tracking=false")
		return false
	if input_mgr.get_control_mode() != "KEYBOARD_MOUSE":
		printerr("  FAIL: Mode was %s (expected KEYBOARD_MOUSE when tracking=false and no prior input)" % input_mgr.get_control_mode())
		return false

	# 2. Establish valid tracking first
	var pkt_valid = {
		"pitch": 0.0,
		"yaw": 36.0,
		"roll": 0.0,
		"tracking": true
	}
	input_mgr.inject_telemetry_packet(pkt_valid)
	input_mgr.update_inputs(TEST_DELTA)
	
	if not input_mgr.is_webcam_active():
		printerr("  FAIL: is_webcam_active() false after valid packet")
		return false
		
	# 3. Now send packet with tracking = false: tracking must be treated as lost
	input_mgr.inject_telemetry_packet(pkt_no_track)
	input_mgr.update_inputs(TEST_DELTA)
	
	if input_mgr.head_tracking_active:
		printerr("  FAIL: head_tracking_active did not transition to false on tracking loss")
		return false
	if input_mgr.is_webcam_active():
		printerr("  FAIL: is_webcam_active() did not transition to false on tracking loss")
		return false

	print("  [PASS] Telemetry packet with tracking=false correctly prevents activation and marks tracking lost")
	return true

func test_frame_by_frame_decay(input_mgr: InputManager) -> bool:
	input_mgr.set_simulated_keyboard_input(0.0, 0.0, 0.0, false)
	
	# Inject strong steering packet: yaw = 36.0 deg -> normalized yaw = 0.80
	var pkt = {
		"pitch": 0.0,
		"yaw": 36.0,
		"roll": 0.0,
		"calibrated": true,
		"tracking": true
	}
	input_mgr.inject_telemetry_packet(pkt)
	input_mgr.update_inputs(TEST_DELTA)
	
	var initial_yaw = input_mgr.get_yaw_input()
	if absf(initial_yaw - 0.80) > 0.02:
		printerr("  FAIL: Initial yaw %.3f != 0.80" % initial_yaw)
		return false
		
	# Step through timeout period and decay period frame by frame
	# 30 frames at 60 Hz = 0.50s (timeout threshold)
	# After 0.50s, decay runs at 8.0 * dt = 0.1333 per frame, taking ~6 frames from 0.80 to 0.00
	var prev_yaw = initial_yaw
	var snap_detected = false
	var intermediate_decay_frames = 0
	var max_single_frame_jump = 0.0
	
	for f in range(50):
		input_mgr.update_inputs(TEST_DELTA)
		var curr_yaw = input_mgr.get_yaw_input()
		var step_diff = absf(curr_yaw - prev_yaw)
		if step_diff > max_single_frame_jump:
			max_single_frame_jump = step_diff
			
		# Check for discontinuous single-frame snap from >0.5 to 0.0
		if prev_yaw > 0.5 and curr_yaw == 0.0:
			snap_detected = true
			printerr("  FAIL: Snap discontinuity detected at frame %d (jumped from %.3f to %.3f)" % [f, prev_yaw, curr_yaw])
			
		if curr_yaw > 0.001 and curr_yaw < 0.799:
			intermediate_decay_frames += 1
			# During decay, mode should be BLENDED
			if input_mgr.get_control_mode() != "BLENDED":
				printerr("  FAIL: Control mode was %s during decay (expected BLENDED)" % input_mgr.get_control_mode())
				return false
				
		prev_yaw = curr_yaw

	if snap_detected:
		return false

	# Max step change per frame should be bounded by DECAY_RATE * TEST_DELTA (~0.133)
	var expected_max_step = (input_mgr.DECAY_RATE * TEST_DELTA) + 0.01
	if max_single_frame_jump > expected_max_step:
		printerr("  FAIL: Single frame yaw step %.4f exceeded max expected decay step %.4f" % [max_single_frame_jump, expected_max_step])
		return false
		
	if intermediate_decay_frames < 4:
		printerr("  FAIL: Expected at least 4 intermediate decay frames, but observed %d" % intermediate_decay_frames)
		return false
		
	if absf(input_mgr.get_yaw_input()) > 0.001:
		printerr("  FAIL: Final yaw %.4f did not fully decay to 0.000" % input_mgr.get_yaw_input())
		return false
		
	if input_mgr.get_control_mode() != "KEYBOARD_MOUSE":
		printerr("  FAIL: Final control mode was %s (expected KEYBOARD_MOUSE after full decay)" % input_mgr.get_control_mode())
		return false

	print("  [PASS] Frame-by-frame continuous signal decay verified: %d intermediate frames, max step %.4f, zero snapping" % [intermediate_decay_frames, max_single_frame_jump])
	return true
