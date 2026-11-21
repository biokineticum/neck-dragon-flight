# ==============================================================================
# test_settings_and_readiness.gd - Unit & E2E Verification for Settings & Ready Start
# ==============================================================================
extends SceneTree

const GameManager = preload("res://scripts/GameManager.gd")
const InputManager = preload("res://scripts/InputManager.gd")
const HUD = preload("res://scripts/HUD.gd")

func _init() -> void:
	print("\n==================================================================")
	print("   STARTING SETTINGS & READINESS VERIFICATION TESTS")
	print("==================================================================")
	
	var passed = await run_tests()
	if passed:
		print("==================================================================")
		print("   ALL SETTINGS & READINESS TESTS PASSED (Exit code 0)")
		print("==================================================================")
		quit(0)
	else:
		printerr("==================================================================")
		printerr("   SETTINGS & READINESS TESTS FAILED (Exit code 1)")
		printerr("==================================================================")
		quit(1)

func run_tests() -> bool:
	var success = true
	var root = get_root()
	
	# Test 1: Startup Readiness State
	print("\n--- Test 1: Startup State is READY and Dragon is Paused ---")
	var gm = GameManager.new()
	root.add_child(gm)
	await process_frame
	
	if gm.get_state() != GameManager.GameState.READY:
		printerr("  FAIL: GameManager initial state is %s, expected READY" % gm.get_state_name())
		success = false
	else:
		print("  [PASS] Initial state correctly set to READY")
		
	gm.start_flight()
	if gm.get_state() != GameManager.GameState.FLYING:
		printerr("  FAIL: GameManager did not transition to FLYING after start_flight()")
		success = false
	else:
		print("  [PASS] Successfully transitioned to FLYING after start_flight()")
	gm.queue_free()
	
	# Test 2: InputManager Live Sensitivity Customization
	print("\n--- Test 2: Sensitivity Sliders & Inversion Scaling ---")
	var im = InputManager.new()
	root.add_child(im)
	await process_frame
	
	im.set_sensitivity_overall(0.5)
	im.set_sensitivity_yaw(1.2)
	im.set_sensitivity_pitch(1.5)
	im.set_invert_pitch(true)
	
	if absf(im.sensitivity_overall - 0.5) > 0.001 or absf(im.sensitivity_yaw - 1.2) > 0.001 or not im.invert_pitch:
		printerr("  FAIL: Sensitivity or invert setter did not apply values")
		success = false
	else:
		print("  [PASS] Setters successfully updated sensitivity & inversion variables")
		
	# Ingest test packet with 10 deg pitch and yaw
	var test_payload = {
		"pitch": 10.0,
		"yaw": 15.0,
		"roll": 0.0,
		"calibrated": true,
		"tracking": true
	}
	im.inject_telemetry_packet(test_payload)
	
	# Expected:
	# pitch: (10.0 * 1.5 * 0.5) = 7.5 deg. Inverted -> -7.5 deg. Normalized (-7.5 / 35.0) = -0.2142857
	# yaw: (15.0 * 1.2 * 0.5) = 9.0 deg. Normalized (9.0 / 45.0) = 0.20
	var expected_pitch = - (10.0 * 1.5 * 0.5) / 35.0
	var expected_yaw = (15.0 * 1.2 * 0.5) / 45.0
	
	if absf(im.webcam_pitch - expected_pitch) > 0.001:
		printerr("  FAIL: webcam_pitch is %f, expected %f" % [im.webcam_pitch, expected_pitch])
		success = false
	else:
		print("  [PASS] Inverted & scaled webcam_pitch computed accurately: %f" % im.webcam_pitch)
		
	if absf(im.webcam_yaw - expected_yaw) > 0.001:
		printerr("  FAIL: webcam_yaw is %f, expected %f" % [im.webcam_yaw, expected_yaw])
		success = false
	else:
		print("  [PASS] Scaled webcam_yaw computed accurately: %f" % im.webcam_yaw)
		
	im.reset_sensitivity_defaults()
	if absf(im.sensitivity_overall - 1.0) > 0.001 or im.invert_pitch:
		printerr("  FAIL: reset_sensitivity_defaults failed to restore 1.0")
		success = false
	else:
		print("  [PASS] reset_sensitivity_defaults restored defaults")
	im.queue_free()
	
	# Test 3: HUD Settings & Ready Panel Interaction
	print("\n--- Test 3: HUD Settings and Ready Panel Navigation ---")
	var container = Node.new()
	root.add_child(container)
	var hud_scene = load("res://scenes/HUD.tscn")
	var hud: HUD = hud_scene.instantiate()
	container.add_child(hud)
	await process_frame
	
	hud.open_settings()
	if hud.settings_panel == null or not hud.settings_panel.visible:
		printerr("  FAIL: open_settings() did not make settings_panel visible")
		success = false
	else:
		print("  [PASS] Settings panel opens on command")
		
	hud.close_settings()
	if hud.settings_panel.visible:
		printerr("  FAIL: close_settings() did not hide settings_panel")
		success = false
	else:
		print("  [PASS] Settings panel closes on command")
		
	hud.show_ready_panel()
	if hud.ready_panel == null or not hud.ready_panel.visible:
		printerr("  FAIL: show_ready_panel() did not show ready panel")
		success = false
	else:
		print("  [PASS] Ready panel displays correctly")
		
	hud.hide_ready_panel()
	if hud.ready_panel.visible:
		printerr("  FAIL: hide_ready_panel() did not hide ready panel")
		success = false
	else:
		print("  [PASS] Ready panel hides on take off")
		
	container.queue_free()
	return success
