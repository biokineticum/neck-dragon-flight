extends SceneTree

# ==============================================================================
# test_input_mock.gd - Headless Mock Input & Blending Smoke Test Suite
# ==============================================================================
# Verifies:
# 1. InputManager packet ingestion, parsing, and normalization bounds [-1.0, 1.0]
# 2. Packet timeout (0.50s) and continuous signal decay (8.0 * delta)
# 3. Dual-mode priority override: keyboard immediately takes 100% authority
# 4. Smooth 0.35s crossfade on keyboard release
# 5. Non-primitive JSON type resilience and tracking loss handling
# 6. Neutral pose calibration ('C')
# ==============================================================================

const InputManager = preload("res://scripts/InputManager.gd")
const TEST_DELTA: float = 1.0 / 60.0

func _init() -> void:
	print("==================================================================")
	print("   STARTING MOCK INPUT & DUAL-MODE BLENDING HEADLESS TESTS")
	print("==================================================================")
	
	var watchdog = create_timer(20.0)
	watchdog.timeout.connect(func():
		printerr("[FATAL] Watchdog timeout (20.0s) exceeded! Terminating code 1.")
		quit(1)
	)
	
	var passed = await run_input_mock_suite()
	if passed:
		print("==================================================================")
		print("   ALL MOCK INPUT TESTS PASSED (Exit code 0)")
		print("   Tests: 6 passed, 0 failed")
		print("==================================================================")
		quit(0)
	else:
		printerr("==================================================================")
		printerr("   MOCK INPUT TESTS FAILED (Exit code 1)")
		printerr("==================================================================")
		quit(1)

func run_input_mock_suite() -> bool:
	var success = true
	var input_mgr = InputManager.new()
	root.add_child(input_mgr)
	await process_frame
	
	# Test 1: Ingestion & Normalization
	print("\n--- Test 1: Telemetry Ingestion & Normalization Bounds ---")
	var t1 = test_normalization(input_mgr)
	print("Test 1 Result: %s" % ("PASS" if t1 else "FAIL"))
	success = t1 and success
	
	# Test 2: Timeout & Decay
	print("\n--- Test 2: Packet Silence Timeout (0.50s) & Signal Decay ---")
	var t2 = test_timeout_decay(input_mgr)
	print("Test 2 Result: %s" % ("PASS" if t2 else "FAIL"))
	success = t2 and success
	
	# Test 3: Keyboard Priority Override
	print("\n--- Test 3: Keyboard Fallback Immediate Priority Override ---")
	var t3 = test_keyboard_override(input_mgr)
	print("Test 3 Result: %s" % ("PASS" if t3 else "FAIL"))
	success = t3 and success
	
	# Test 4: 0.35s Release Crossfade
	print("\n--- Test 4: Keyboard Release 0.35s Smooth Crossfade ---")
	var t4 = test_crossfade(input_mgr)
	print("Test 4 Result: %s" % ("PASS" if t4 else "FAIL"))
	success = t4 and success
	
	# Test 5: Neutral Calibration
	print("\n--- Test 5: Runtime Neutral Pose Calibration ('C') ---")
	var t5 = test_neutral_calibration(input_mgr)
	print("Test 5 Result: %s" % ("PASS" if t5 else "FAIL"))
	success = t5 and success
	
	# Test 6: Malformed Payload Resilience
	print("\n--- Test 6: Malformed Payload & Tracking Loss Resilience ---")
	var t6 = test_malformed_and_tracking_loss(input_mgr)
	print("Test 6 Result: %s" % ("PASS" if t6 else "FAIL"))
	success = t6 and success
	
	input_mgr.queue_free()
	await process_frame
	return success

func test_normalization(input_mgr: InputManager) -> bool:
	var pkt = {"pitch": -35.0, "yaw": 45.0, "roll": -17.5, "calibrated": true, "tracking": true}
	input_mgr.inject_telemetry_packet(pkt)
	input_mgr.update_inputs(TEST_DELTA)
	
	if not input_mgr.is_webcam_active():
		printerr("  FAIL: is_webcam_active() false after packet")
		return false
	if absf(input_mgr.get_pitch_input() - (-1.0)) > 0.02:
		printerr("  FAIL: Pitch not normalized to -1.0")
		return false
	if absf(input_mgr.get_yaw_input() - 1.0) > 0.02:
		printerr("  FAIL: Yaw not normalized to 1.0")
		return false
	if absf(input_mgr.get_roll_input() - (-0.5)) > 0.02:
		printerr("  FAIL: Roll not normalized to -0.5")
		return false
		
	print("  [PASS] Ingestion and clamping to [-1.0, 1.0] verified")
	return true

func test_timeout_decay(input_mgr: InputManager) -> bool:
	# Advance 45 frames (~0.75s > 0.50s timeout + decay window)
	for i in range(45):
		input_mgr.update_inputs(TEST_DELTA)
		
	if input_mgr.is_webcam_active():
		printerr("  FAIL: is_webcam_active() remained true after 0.60s silence")
		return false
	if absf(input_mgr.get_yaw_input()) > 0.05:
		printerr("  FAIL: Yaw failed to decay below 0.05")
		return false
		
	print("  [PASS] Timeout and smooth signal decay confirmed")
	return true

func test_keyboard_override(input_mgr: InputManager) -> bool:
	var pkt = {"pitch": 0.0, "yaw": 30.0, "roll": 0.0, "tracking": true}
	input_mgr.inject_telemetry_packet(pkt)
	input_mgr.update_inputs(TEST_DELTA)
	
	input_mgr.set_simulated_keyboard_input(-1.0, 0.0, 0.0, true)
	input_mgr.update_inputs(TEST_DELTA)
	
	if input_mgr.get_control_mode() != "KEYBOARD_MOUSE":
		printerr("  FAIL: Mode was not KEYBOARD_MOUSE on key press")
		return false
	if absf(input_mgr.get_pitch_input() - (-1.0)) > 0.01:
		printerr("  FAIL: Manual pitch did not take 100% authority")
		return false
		
	print("  [PASS] Keyboard input overrides webcam with 100% authority")
	return true

func test_crossfade(input_mgr: InputManager) -> bool:
	var pkt = {"pitch": 0.0, "yaw": 36.0, "roll": 0.0, "tracking": true}
	# Release keyboard
	input_mgr.set_simulated_keyboard_input(0.0, 0.0, 0.0, false)
	input_mgr.inject_telemetry_packet(pkt)
	
	# Step into crossfade
	for i in range(6):
		input_mgr.inject_telemetry_packet(pkt)
		input_mgr.update_inputs(TEST_DELTA)
		
	if input_mgr.get_control_mode() != "BLENDED":
		printerr("  FAIL: Mode was not BLENDED during release crossfade")
		return false
		
	# Complete crossfade
	for i in range(20):
		input_mgr.inject_telemetry_packet(pkt)
		input_mgr.update_inputs(TEST_DELTA)
		
	if input_mgr.get_control_mode() != "WEBCAM":
		printerr("  FAIL: Mode was not WEBCAM after crossfade completion")
		return false
		
	print("  [PASS] 0.35s crossfade from manual release to webcam verified")
	return true

func test_neutral_calibration(input_mgr: InputManager) -> bool:
	var pkt = {"pitch": 10.0, "yaw": -15.0, "roll": 5.0, "tracking": true}
	input_mgr.inject_telemetry_packet(pkt)
	input_mgr.update_inputs(TEST_DELTA)
	
	input_mgr.calibrate_neutral()
	input_mgr.inject_telemetry_packet(pkt)
	input_mgr.update_inputs(TEST_DELTA)
	
	if absf(input_mgr.get_pitch_input()) > 0.02 or absf(input_mgr.get_yaw_input()) > 0.02:
		printerr("  FAIL: calibrate_neutral did not zero effective steering outputs")
		return false
		
	input_mgr.reset_calibration()
	print("  [PASS] Neutral pose calibration zeroes current orientation angles")
	return true

func test_malformed_and_tracking_loss(input_mgr: InputManager) -> bool:
	# Tracking false packet
	var pkt_loss = {"pitch": 20.0, "yaw": 20.0, "roll": 0.0, "tracking": false}
	input_mgr.inject_telemetry_packet(pkt_loss)
	input_mgr.update_inputs(TEST_DELTA)
	
	if input_mgr.is_webcam_active():
		printerr("  FAIL: is_webcam_active() true when tracking=false")
		return false
		
	# Malformed payload
	var parsed = input_mgr.process_json_packet('{"pitch": [1, 2], "yaw": null}')
	if not parsed:
		printerr("  FAIL: process_json_packet crashed on non-primitive JSON")
		return false
		
	print("  [PASS] Malformed JSON types and tracking loss handled gracefully")
	return true
