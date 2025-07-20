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

        # 初期の進行方向をランダムに設定
        angle = random.uniform(0, 2 * math.pi)
        self.vx = math.cos(angle) * BALL_SPEED
        self.vy = math.sin(angle) * BALL_SPEED

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
        # タイムはフレーム単位で管理 (200秒 * 60fps)
        self.time = 200 * 60
        self.game_over = False

        # フィールドを初期化（外周を壁で囲む）
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

        # プレイヤーを中央に配置
        self.player = Player(FIELD_GRID_WIDTH // 2, FIELD_GRID_HEIGHT // 2)

        # ボールを1つ生成
        self.balls = [Ball()]

        # スコアボーナスの達成状況を管理
        self.time_bonus_checkpoints = [400, 1000, 1600, 2200, 2800, 3400]
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
        # 修正点: 6フレームに1回だけプレイヤーの更新処理を行う
        if pyxel.frame_count % 6 != 0:
            return

        old_x, old_y = self.player.x, self.player.y
        moved = False

        # キー入力による移動
        if pyxel.btn(pyxel.KEY_LEFT):
            self.player.x -= 1
            moved = True
        elif pyxel.btn(pyxel.KEY_RIGHT):
            self.player.x += 1
            moved = True
        elif pyxel.btn(pyxel.KEY_UP):
            self.player.y -= 1
            moved = True

        # 移動先が壁やブロックなら移動をキャンセル
        if self.field[self.player.y][self.player.x] != EMPTY:
            self.player.x, self.player.y = old_x, old_y
            moved = False

        if moved:
            # 移動が確定した場合、移動元の位置にブロックを置く
            self.field[old_y][old_x] = BLOCK
        else:
            # キー入力がない場合、下に移動（ブロックは置かない）
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
            ball.update()
            self.handle_ball_collisions(ball)

    def handle_ball_collisions(self, ball):
        """ボールと壁、ブロック、プレイヤーとの衝突を処理"""
        # --- 壁・ブロックとの衝突 ---
        hit_x = False
        hit_y = False

        # X方向の衝突判定
        grid_y_top = int((ball.y - BALL_RADIUS - (FIELD_TOP_Y * GRID_SIZE)) / GRID_SIZE)
        grid_y_bottom = int(
            (ball.y + BALL_RADIUS - (FIELD_TOP_Y * GRID_SIZE)) / GRID_SIZE
        )

        if ball.vx > 0:  # 右へ移動中
            grid_x = int((ball.x + BALL_RADIUS) / GRID_SIZE)
            if self.is_obstacle(grid_x, grid_y_top) or self.is_obstacle(
                grid_x, grid_y_bottom
            ):
                self.handle_block_hit(grid_x, grid_y_top)
                self.handle_block_hit(grid_x, grid_y_bottom)
                hit_x = True
        elif ball.vx < 0:  # 左へ移動中
            grid_x = int((ball.x - BALL_RADIUS) / GRID_SIZE)
            if self.is_obstacle(grid_x, grid_y_top) or self.is_obstacle(
                grid_x, grid_y_bottom
            ):
                self.handle_block_hit(grid_x, grid_y_top)
                self.handle_block_hit(grid_x, grid_y_bottom)
                hit_x = True

        # Y方向の衝突判定
        grid_x_left = int((ball.x - BALL_RADIUS) / GRID_SIZE)
        grid_x_right = int((ball.x + BALL_RADIUS) / GRID_SIZE)

        if ball.vy > 0:  # 下へ移動中
            grid_y = int((ball.y + BALL_RADIUS - (FIELD_TOP_Y * GRID_SIZE)) / GRID_SIZE)
            if self.is_obstacle(grid_x_left, grid_y) or self.is_obstacle(
                grid_x_right, grid_y
            ):
                self.handle_block_hit(grid_x_left, grid_y)
                self.handle_block_hit(grid_x_right, grid_y)
                hit_y = True
        elif ball.vy < 0:  # 上へ移動中
            grid_y = int((ball.y - BALL_RADIUS - (FIELD_TOP_Y * GRID_SIZE)) / GRID_SIZE)
            if self.is_obstacle(grid_x_left, grid_y) or self.is_obstacle(
                grid_x_right, grid_y
            ):
                self.handle_block_hit(grid_x_left, grid_y)
                self.handle_block_hit(grid_x_right, grid_y)
                hit_y = True

        # --- 修正点: より自然な反射ロジック ---
        if hit_x and hit_y:  # 角に当たった場合
            ball.vx *= -1
            ball.vy *= -1
        elif hit_x:  # 左右の壁/ブロックに当たった場合
            ball.vx *= -1
            # 膠着状態を防ぐため、垂直方向の速度に僅かなランダム性を加える
            ball.vy += random.uniform(-0.1, 0.1)
        elif hit_y:  # 上下の壁/ブロックに当たった場合
            ball.vy *= -1
            # 膠着状態を防ぐため、水平方向の速度に僅かなランダム性を加える
            ball.vx += random.uniform(-0.1, 0.1)

        # 速度を正規化して、常に一定の速さを保つ
        if hit_x or hit_y:
            current_speed = math.sqrt(ball.vx**2 + ball.vy**2)
            if current_speed > 0:
                ball.vx = (ball.vx / current_speed) * BALL_SPEED
                ball.vy = (ball.vy / current_speed) * BALL_SPEED
        # --- 修正ここまで ---

        # --- プレイヤーとの衝突 ---
        player_px = (self.player.x + 0.5) * GRID_SIZE
        player_py = (self.player.y + 0.5 + FIELD_TOP_Y) * GRID_SIZE
        dist_x = ball.x - player_px
        dist_y = ball.y - player_py
        if dist_x**2 + dist_y**2 < (BALL_RADIUS + GRID_SIZE // 2) ** 2:
            self.time = max(0, self.time - 100 * 60)  # 100秒減らす
            # プレイヤーから離れるようにボールを反射
            norm = math.sqrt(dist_x**2 + dist_y**2)
            if norm > 0:
                ball.vx = (dist_x / norm) * BALL_SPEED
                ball.vy = (dist_y / norm) * BALL_SPEED
            else:  # まれに中心で衝突した場合
                ball.vx *= -1
                ball.vy *= -1

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

        # スコアボーナスチェック
        # タイム追加
        for i, score_req in enumerate(self.time_bonus_checkpoints):
            if not self.time_bonus_achieved[i] and self.score >= score_req:
                self.time += 50 * 60  # 50秒追加
                self.time_bonus_achieved[i] = True

        # ボール追加
        for i, score_req in enumerate(self.ball_add_checkpoints):
            if not self.ball_add_achieved[i] and self.score >= score_req:
                if len(self.balls) < MAX_BALLS:
                    self.balls.append(Ball())
                self.ball_add_achieved[i] = True

    def draw(self):
        """画面全体を描画"""
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.game_over:
            self.draw_game_over()
            return

        self.draw_hud()
        self.draw_field()
        self.player.draw()
        for ball in self.balls:
            ball.draw()

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

    def draw_game_over(self):
        """ゲームオーバー画面を表示"""
        text = "GAME OVER"
        x = (SCREEN_WIDTH - len(text) * 4) / 2
        y = SCREEN_HEIGHT / 2 - 8
        pyxel.text(x, y, text, pyxel.COLOR_RED)

        score_text = f"FINAL SCORE: {self.score}"
        x = (SCREEN_WIDTH - len(score_text) * 4) / 2
        pyxel.text(x, y + 10, score_text, pyxel.COLOR_WHITE)

        restart_text = "PRESS ENTER TO RESTART"
        x = (SCREEN_WIDTH - len(restart_text) * 4) / 2
        pyxel.text(x, y + 30, restart_text, pyxel.COLOR_LIME)


# ゲームを開始
Game()
