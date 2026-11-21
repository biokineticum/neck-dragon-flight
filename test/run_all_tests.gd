extends SceneTree

# ==============================================================================
# run_all_tests.gd - Master Headless Smoke Test Runner
# ==============================================================================
# Executes all test suites sequentially via headless sub-processes:
# 1. test/test_milestone2_headless.gd
# 2. test/test_flight_physics.gd
# 3. test/test_collision.gd
# 4. test/test_input_mock.gd
# 5. test/test_tier5_adversarial_engine.gd
# Logs aggregate summary report with "passed" and "failed" counts.
# Exits code 0 on 100% pass, or code 1 on any failure.
# ==============================================================================

const TEST_BATTERY: Array[String] = [
	"test/test_milestone1_peaceful_openworld.gd",
	"test/test_heart_collectibles.gd",
	"test/test_milestone2_headless.gd",
	"test/test_flight_physics.gd",
	"test/test_collision.gd",
	"test/test_input_mock.gd",
	"test/test_tier5_adversarial_engine.gd",
	"test/test_settings_and_readiness.gd"
]

func _init() -> void:
	print("==================================================================")
	print("   DRAGON FLIGHT GAME - MASTER HEADLESS SMOKE TEST BATTERY")
	print("==================================================================")
	
	# Master watchdog (90.0s total limit)
	var watchdog = create_timer(90.0)
	watchdog.timeout.connect(func():
		printerr("\n[FATAL] Master test watchdog (90.0s) exceeded! Aborting.")
		quit(1)
	)
	
	var godot_bin = OS.get_executable_path()
	print("Engine Binary: %s" % godot_bin)
	print("Working Directory: %s" % ProjectSettings.globalize_path("res://"))
	
	var passed_count = 0
	var failed_count = 0
	var total_tests = 0
	var results: Array[Dictionary] = []
	
	for test_script in TEST_BATTERY:
		if not FileAccess.file_exists("res://" + test_script):
			print("[SKIP] %s not found in workspace, skipping." % test_script)
			continue
			
		total_tests += 1
		print("\n------------------------------------------------------------------")
		print(">> RUNNING SUITE: %s" % test_script)
		print("------------------------------------------------------------------")
		
		var output: Array = []
		var args: PackedStringArray = [
			"--headless",
			"--path", ".",
			"-s", test_script
		]
		
		var start_msec = Time.get_ticks_msec()
		var exit_code = OS.execute(godot_bin, args, output, true)
		var elapsed_sec = (Time.get_ticks_msec() - start_msec) / 1000.0
		
		var log_output = "".join(output)
		print(log_output)
		
		if exit_code == 0:
			passed_count += 1
			print(">> RESULT: [PASS] %s (%.2fs)" % [test_script, elapsed_sec])
			results.append({"suite": test_script, "status": "PASS", "time": elapsed_sec})
		else:
			failed_count += 1
			printerr(">> RESULT: [FAIL] %s (exit code %d, %.2fs)" % [test_script, exit_code, elapsed_sec])
			results.append({"suite": test_script, "status": "FAIL", "time": elapsed_sec})
			
	# Print Master Summary Report
	print("\n==================================================================")
	print("   MASTER SMOKE TEST BATTERY REPORT")
	print("==================================================================")
	for res in results:
		print("   [%s] %s (%.2fs)" % [res.status, res.suite, res.time])
	print("------------------------------------------------------------------")
	print("   Summary: %d passed, %d failed (Total %d suites executed)" % [passed_count, failed_count, total_tests])
	print("==================================================================")
	
	if failed_count == 0 and total_tests > 0:
		print("MASTER SMOKE BATTERY: ALL TESTS PASSED.")
		quit(0)
	else:
		printerr("MASTER SMOKE BATTERY: DETECTED FAILURES. EXITING CODE 1.")
		quit(1)
