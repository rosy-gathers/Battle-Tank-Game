# Battle-Tank-Game
Battle tanks is a game project made on OpenGL. It involves the player controlling a tank, it goes through three levels with increasing enemy number and variety until it reaches the final “Boss” level where they face off against a very powerful enemy. The enemy waves and the bosses will be tanks as well. In the first three levels, the player will gain access to a different tank with different capabilities.
 
Features
 
1) 360-degree camera view and camera control (the barrel of the player tank will 360 degree rotatable - barrel can rotate while the body remains at rest and the body+barrel can rotate together)
2) Player’s ability to shift perspective between first and third person
3) The player’s inherent movement ability is to accelerate and decelerate and strafe
4) Player tank at each level will obtain upgrades and special powers in the forming of modes the tank can change into. Per level obtained mode list is below:
a) LEVEL-1: The initial mode the player tank will be with starting abilities (firing one bullet at a time normally at a constant speed)
b) LEVEL-2: This is the mode where the tank is stronger (more health) but is slower, has more health, along with stronger bullets with no cooldown greater bullet speeds
c) LEVEL-3: This is the mode where the tank shoots multiple bullets forward
d) LEVEL-4: This is the mode where (final boss) player will shoot two consecutive fireballs at the final boss 


5) Each level will bring increased enemy waves along with a level mini-boss at the end with different abilities
6) Each level miniboss abilities are listed below:
	a. First level: Higher health(10hp)  than normal enemies and greater bullet speed than normal enemies
	b. Second level: Miniboss immobile at the center of the map. The player will be shifted to a corner at the start. The enemy is immobile but has a much greater bullet speed than normal enemies, i.e. even more than the first miniboss. The miniboss will have a radius around it where if the player approaches, it will lose health
	c. Third level: Miniboss will be three, they will be faster than  normal and can shoot three bullets at a time.
7) Cheat mode - tank will become indestructible, health will not be affected even if bullets hit the player tank and will have no cooldown. 
8)  The final boss will have higher health than other minibosses, and will shoot multiple (four) bullets at a time. It will stop at its position, and shoot a laser beam at the player position, and if the player is caught in the laser beam only, it dies and the game is instantly over. The final boss will follow a pattern of:
	4Bullets→Laser beam→4Bullets→Laser beam (loop)

Work Steps: 
Tank movement (accelerate, decelerate, strafe) and barrel 360° rotation
Initial tank model and bullet control
First/Third-person camera toggle & camera control
Cheat mode (invincibility, no cooldown)
Normal enemy waves (movement + shooting)
Minibosses (Level 1–3 with unique abilities)
Arena/world (wall, visual polish)
HUD/Banner, player/enemy health, damage
Player tank upgrades
Level progression (3 levels + final boss)
Final boss level  (multi-phase: bullets, missiles, laser beam pattern)
Bullets & projectiles system upgrade (damage, cooldowns, multi-shot, missiles)













