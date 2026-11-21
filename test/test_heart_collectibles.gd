extends SceneTree

const Terrain = preload("res://scripts/ProceduralMeshGen.gd")

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var main = load("res://scenes/Main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	var player = main.get_node("PlayerDragon")
	var game = main.get_node("GameManager")
	var hearts = main.get_node("HeartCollectibles")
	var hud = main.get_node("HUD")
	hearts.set_physics_process(false)
	player.get_node("FlightController").set_physics_process(false)
	var ok = true
	if hearts.hearts.size() != 5 or hearts.collected != 0 or hud.collectible_hearts.text != "♥ SERCA: 0 / 5":
		printerr("FAIL: Initial hearts or HUD")
		ok = false
	for heart in hearts.hearts:
		var p = heart.global_position
		var ground = Terrain.sample_landscape_surface(p.x, p.z, 3000.0, 140, 42)
		if p.y < ground + 21.9:
			printerr("FAIL: Heart below safe terrain clearance")
			ok = false
		if Vector2(p.x, p.z).distance_to(Vector2(player.global_position.x, player.global_position.z)) < 200.0:
			printerr("FAIL: Heart starts too close to the dragon")
			ok = false
	for i in range(hearts.hearts.size()):
		for j in range(i + 1, hearts.hearts.size()):
			var a = hearts.hearts[i].global_position
			var b = hearts.hearts[j].global_position
			if Vector2(a.x, a.z).distance_to(Vector2(b.x, b.z)) < hearts.MIN_HEART_SPACING:
				printerr("FAIL: Hearts are clustered")
				ok = false
	# Passing through a heart while waiting to start must not collect it.
	player.global_position = hearts.hearts[0].global_position
	hearts._physics_process(0.016)
	if hearts.collected != 0:
		printerr("FAIL: Collected while READY")
		ok = false
	game.start_flight()
	var missed = hearts.hearts[0]
	missed.global_position = player.global_position + Vector3(1000, 0, 0)
	hearts.previous_position = player.global_position
	hearts._physics_process(0.016)
	if missed.global_position.distance_to(player.global_position) > hearts.MAX_DISTANCE or hearts.collected != 0:
		printerr("FAIL: Missed heart was not relocated without collection")
		ok = false
	# A segment crossing a heart, with both endpoints outside the radius, must collect.
	for i in range(10):
		var heart = hearts.hearts[0]
		var target = heart.global_position
		hearts.previous_position = target + Vector3(0, 0, 12)
		player.global_position = target + Vector3(0, 0, -12)
		# Keep other targets away from this artificial teleport.
		for j in range(1, hearts.hearts.size()):
			hearts.hearts[j].global_position = target + Vector3(100 + j * 20, 100, 0)
		hearts._physics_process(0.016)
		var expected = (i % 5) + 1
		if hearts.collected != expected or hud.collectible_hearts.text != "♥ SERCA: %d / 5" % expected:
			printerr("FAIL: Collection or HUD at pickup %d" % (i + 1))
			ok = false
		if expected == 5 and (hearts.firework_time < 0.0 or hearts.sparks.size() != 120):
			printerr("FAIL: No fireworks after pickup %d" % (i + 1))
			ok = false
		if expected == 4 and i == 3 and hearts.firework_time >= 0.0:
			printerr("FAIL: Fireworks started before five hearts")
			ok = false
	hearts._update_fireworks(hearts.FIREWORK_DURATION)
	if hearts.firework_time >= 0.0 or not hearts.sparks.is_empty():
		printerr("FAIL: Fireworks did not clean up")
		ok = false
	hearts._start_fireworks()
	game.reset_game(game.GameState.READY)
	if hearts.collected != 0 or hearts.hearts.size() != 5 or hud.collectible_hearts.text != "♥ SERCA: 0 / 5" or hearts.firework_time >= 0.0 or not hearts.sparks.is_empty():
		printerr("FAIL: Restart did not reset hearts")
		ok = false
	main.queue_free()
	await process_frame
	if ok:
		print("Heart collection, repeated fireworks and restart: PASS")
		quit(0)
	else:
		quit(1)
