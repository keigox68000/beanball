import pyxel
import random
import math

# --- 定数設定 ---
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 200
GRID_SIZE = 8

# グリッド単位のフィールドサイズ
# 一番上の行はスコア表示用なので、高さは1減らす
FIELD_GRID_WIDTH = SCREEN_WIDTH // GRID_SIZE
FIELD_GRID_HEIGHT = (SCREEN_HEIGHT // GRID_SIZE) - 1
FIELD_TOP_Y = 1  # フィールドが開始するY座標（グリッド単位）

# フィールドの状態を表す定数
EMPTY = 0
WALL = 1
BLOCK = 2

# ボールの設定
BALL_RADIUS = 3
MAX_BALLS = 8
BALL_SPEED = 2

# プレイヤーの色
PLAYER_COLOR = pyxel.COLOR_WHITE
# ボールの色
BALL_COLOR = pyxel.COLOR_YELLOW
# ブロックの色
BLOCK_COLOR = pyxel.COLOR_CYAN
# 壁の色
WALL_COLOR = pyxel.COLOR_GRAY


class Player:
    """プレイヤーを管理するクラス"""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.is_alive = True

    def draw(self):
        """プレイヤー（三角形）を描画"""
        px = self.x * GRID_SIZE
        py = (self.y + FIELD_TOP_Y) * GRID_SIZE
        # 上向きの三角形を描画
        pyxel.tri(
            px + GRID_SIZE // 2,
            py + 1,
            px + 1,
            py + GRID_SIZE - 1,
            px + GRID_SIZE - 2,
            py + GRID_SIZE - 1,
            PLAYER_COLOR,
        )


class Ball:
    """ボールを管理するクラス"""

    def __init__(self):
        # 壁やブロックと重ならないように初期位置を設定
        self.x = random.uniform(GRID_SIZE * 2, SCREEN_WIDTH - GRID_SIZE * 2)
        self.y = random.uniform(
            GRID_SIZE * (FIELD_TOP_Y + 2), SCREEN_HEIGHT - GRID_SIZE * 2
        )

        # 初期の進行方向を45度のいずれかに設定
        vx = random.choice([-1, 1])
        vy = random.choice([-1, 1])

        # ベクトルを正規化して、速度をBALL_SPEEDに設定
        norm = math.sqrt(vx**2 + vy**2)  # この値は常に√2
        self.vx = (vx / norm) * BALL_SPEED
        self.vy = (vy / norm) * BALL_SPEED

    def update(self):
        """ボールの位置を更新"""
        self.x += self.vx
        self.y += self.vy

    def draw(self):
        """ボール（円）を描画"""
        pyxel.circ(self.x, self.y, BALL_RADIUS, BALL_COLOR)


class Game:
    """ゲーム全体を管理するクラス"""

    def __init__(self):
        """ゲームの初期化"""
        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Block Placer", fps=60)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self):
        """ゲームの状態をリセット"""
        self.score = 0
        self.time = 200 * 60
        self.game_over = False

        self.field = [[EMPTY] * FIELD_GRID_WIDTH for _ in range(FIELD_GRID_HEIGHT)]
        for y in range(FIELD_GRID_HEIGHT):
            for x in range(FIELD_GRID_WIDTH):
                if (
                    x == 0
                    or x == FIELD_GRID_WIDTH - 1
                    or y == 0
                    or y == FIELD_GRID_HEIGHT - 1
                ):
                    self.field[y][x] = WALL

        self.player = Player(FIELD_GRID_WIDTH // 2, FIELD_GRID_HEIGHT // 2)
        self.balls = [Ball()]

        self.time_bonus_checkpoints = [400, 1000, 1600, 2200, 2800, 3400]
        # --- 修正点: ボールが増えるスコアのタイミングを変更 ---
        self.ball_add_checkpoints = [200, 400, 800, 1000, 1400, 1600, 2000]
        self.time_bonus_achieved = [False] * len(self.time_bonus_checkpoints)
        self.ball_add_achieved = [False] * len(self.ball_add_checkpoints)

    def update(self):
        """ゲームの状態をフレームごとに更新"""
        if self.game_over:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        self.update_player()
        self.update_balls()
        self.update_time_and_score()

    def update_player(self):
        """プレイヤーの移動とブロック設置を処理"""
        if pyxel.frame_count % 6 != 0:
            return

        old_x, old_y = self.player.x, self.player.y
        moved = False

        if pyxel.btn(pyxel.KEY_LEFT):
            self.player.x -= 1
            moved = True
        elif pyxel.btn(pyxel.KEY_RIGHT):
            self.player.x += 1
            moved = True
        elif pyxel.btn(pyxel.KEY_UP):
            self.player.y -= 1
            moved = True

        if self.field[self.player.y][self.player.x] != EMPTY:
            self.player.x, self.player.y = old_x, old_y
            moved = False

        if moved:
            self.field[old_y][old_x] = BLOCK
        else:
            if not (
                pyxel.btn(pyxel.KEY_LEFT)
                or pyxel.btn(pyxel.KEY_RIGHT)
                or pyxel.btn(pyxel.KEY_UP)
            ):
                next_y = self.player.y + 1
                if self.field[next_y][self.player.x] == EMPTY:
                    self.player.y = next_y

    def update_balls(self):
        """ボールの移動と衝突判定を処理"""
        for ball in self.balls:
            self.handle_wall_block_collisions(ball)
            self.handle_player_collision(ball)

    def handle_wall_block_collisions(self, ball):
        """ボールと壁・ブロックの衝突を処理 (めり込み対策版)"""

        # --- 1. X軸方向の移動と衝突解決 ---
        ball.x += ball.vx

        if ball.vx > 0:  # 右へ
            grid_x = int((ball.x + BALL_RADIUS) / GRID_SIZE)
            check_y1 = int((ball.y - BALL_RADIUS - FIELD_TOP_Y * GRID_SIZE) / GRID_SIZE)
            check_y2 = int((ball.y + BALL_RADIUS - FIELD_TOP_Y * GRID_SIZE) / GRID_SIZE)
            hit1 = self.is_obstacle(grid_x, check_y1)
            hit2 = self.is_obstacle(grid_x, check_y2)
            if hit1 or hit2:
                ball.x = grid_x * GRID_SIZE - BALL_RADIUS - 0.01  # わずかに押し戻す
                ball.vx *= -1
                if hit1:
                    self.handle_block_hit(grid_x, check_y1)
                if hit2:
                    self.handle_block_hit(grid_x, check_y2)
        elif ball.vx < 0:  # 左へ
            grid_x = int((ball.x - BALL_RADIUS) / GRID_SIZE)
            check_y1 = int((ball.y - BALL_RADIUS - FIELD_TOP_Y * GRID_SIZE) / GRID_SIZE)
            check_y2 = int((ball.y + BALL_RADIUS - FIELD_TOP_Y * GRID_SIZE) / GRID_SIZE)
            hit1 = self.is_obstacle(grid_x, check_y1)
            hit2 = self.is_obstacle(grid_x, check_y2)
            if hit1 or hit2:
                ball.x = (
                    (grid_x + 1) * GRID_SIZE + BALL_RADIUS + 0.01
                )  # わずかに押し戻す
                ball.vx *= -1
                if hit1:
                    self.handle_block_hit(grid_x, check_y1)
                if hit2:
                    self.handle_block_hit(grid_x, check_y2)

        # --- 2. Y軸方向の移動と衝突解決 ---
        ball.y += ball.vy

        if ball.vy > 0:  # 下へ
            grid_y = int((ball.y + BALL_RADIUS - FIELD_TOP_Y * GRID_SIZE) / GRID_SIZE)
            check_x1 = int((ball.x - BALL_RADIUS) / GRID_SIZE)
            check_x2 = int((ball.x + BALL_RADIUS) / GRID_SIZE)
            hit1 = self.is_obstacle(check_x1, grid_y)
            hit2 = self.is_obstacle(check_x2, grid_y)
            if hit1 or hit2:
                ball.y = (
                    (grid_y + FIELD_TOP_Y) * GRID_SIZE - BALL_RADIUS - 0.01
                )  # わずかに押し戻す
                ball.vy *= -1
                if hit1:
                    self.handle_block_hit(check_x1, grid_y)
                if hit2:
                    self.handle_block_hit(check_x2, grid_y)
        elif ball.vy < 0:  # 上へ
            grid_y = int((ball.y - BALL_RADIUS - FIELD_TOP_Y * GRID_SIZE) / GRID_SIZE)
            check_x1 = int((ball.x - BALL_RADIUS) / GRID_SIZE)
            check_x2 = int((ball.x + BALL_RADIUS) / GRID_SIZE)
            hit1 = self.is_obstacle(check_x1, grid_y)
            hit2 = self.is_obstacle(check_x2, grid_y)
            if hit1 or hit2:
                ball.y = (
                    (grid_y + 1 + FIELD_TOP_Y) * GRID_SIZE + BALL_RADIUS + 0.01
                )  # わずかに押し戻す
                ball.vy *= -1
                if hit1:
                    self.handle_block_hit(check_x1, grid_y)
                if hit2:
                    self.handle_block_hit(check_x2, grid_y)

    def handle_player_collision(self, ball):
        """プレイヤーとの衝突を処理"""
        player_px = (self.player.x + 0.5) * GRID_SIZE
        player_py = (self.player.y + 0.5 + FIELD_TOP_Y) * GRID_SIZE
        dist_x = ball.x - player_px
        dist_y = ball.y - player_py
        if dist_x**2 + dist_y**2 < (BALL_RADIUS + GRID_SIZE // 2) ** 2:
            self.time = max(0, self.time - 100 * 60)  # 100秒減らす
            norm = math.sqrt(dist_x**2 + dist_y**2)
            if norm > 0:
                ball.vx = (dist_x / norm) * BALL_SPEED
                ball.vy = (dist_y / norm) * BALL_SPEED
            else:
                angle = random.uniform(0, 2 * math.pi)
                ball.vx = math.cos(angle) * BALL_SPEED
                ball.vy = math.sin(angle) * BALL_SPEED

    def is_obstacle(self, x, y):
        """指定されたグリッド座標が障害物（壁かブロック）か判定"""
        if 0 <= y < FIELD_GRID_HEIGHT and 0 <= x < FIELD_GRID_WIDTH:
            return self.field[y][x] in (WALL, BLOCK)
        return False

    def handle_block_hit(self, x, y):
        """ボールがブロックに当たった時の処理"""
        if 0 <= y < FIELD_GRID_HEIGHT and 0 <= x < FIELD_GRID_WIDTH:
            if self.field[y][x] == BLOCK:
                self.field[y][x] = EMPTY
                self.score += 10

    def update_time_and_score(self):
        """時間とスコアを更新し、ボーナスをチェック"""
        if self.time > 0:
            self.time -= 1
        else:
            self.game_over = True

        for i, score_req in enumerate(self.time_bonus_checkpoints):
            if not self.time_bonus_achieved[i] and self.score >= score_req:
                self.time += 50 * 60
                self.time_bonus_achieved[i] = True

        for i, score_req in enumerate(self.ball_add_checkpoints):
            if not self.ball_add_achieved[i] and self.score >= score_req:
                if len(self.balls) < MAX_BALLS:
                    self.balls.append(Ball())
                self.ball_add_achieved[i] = True

    def draw(self):
        """画面全体を描画"""
        pyxel.cls(pyxel.COLOR_BLACK)

        self.draw_hud()
        self.draw_field()
        self.player.draw()
        for ball in self.balls:
            ball.draw()

        if self.game_over:
            self.draw_game_over_overlay()

    def draw_hud(self):
        """スコアと時間を表示"""
        score_text = f"SCORE: {self.score}"
        time_text = f"TIME: {self.time // 60}"
        pyxel.text(5, 4, score_text, pyxel.COLOR_ORANGE)
        pyxel.text(
            SCREEN_WIDTH - len(time_text) * 4 - 5, 4, time_text, pyxel.COLOR_ORANGE
        )

    def draw_field(self):
        """フィールド（壁とブロック）を描画"""
        for y in range(FIELD_GRID_HEIGHT):
            for x in range(FIELD_GRID_WIDTH):
                if self.field[y][x] == WALL:
                    pyxel.rect(
                        x * GRID_SIZE,
                        (y + FIELD_TOP_Y) * GRID_SIZE,
                        GRID_SIZE,
                        GRID_SIZE,
                        WALL_COLOR,
                    )
                elif self.field[y][x] == BLOCK:
                    pyxel.rect(
                        x * GRID_SIZE,
                        (y + FIELD_TOP_Y) * GRID_SIZE,
                        GRID_SIZE,
                        GRID_SIZE,
                        BLOCK_COLOR,
                    )

    def draw_game_over_overlay(self):
        """ゲームオーバーのテキストを画面に重ねて表示"""
        text_w = 120
        text_h = 40
        bg_x = (SCREEN_WIDTH - text_w) / 2
        bg_y = (SCREEN_HEIGHT - text_h) / 2 - 10
        pyxel.rect(bg_x, bg_y, text_w, text_h, pyxel.COLOR_BLACK)

        text = "GAME OVER"
        x = (SCREEN_WIDTH - len(text) * 4) / 2
        y = SCREEN_HEIGHT / 2 - 8
        pyxel.text(x, y, text, pyxel.COLOR_RED)

        score_text = f"FINAL SCORE: {self.score}"
        x = (SCREEN_WIDTH - len(score_text) * 4) / 2
        pyxel.text(x, y + 10, score_text, pyxel.COLOR_WHITE)

        restart_text = "PRESS ENTER"
        x = (SCREEN_WIDTH - len(restart_text) * 4) / 2
        pyxel.text(x, y + 22, restart_text, pyxel.COLOR_LIME)


# ゲームを開始
Game()
