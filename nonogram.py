#!/usr/bin/env python3
"""nonogram —— 终端数织（Nonogram / Picross）小玩具.

生成对称小谜题、行列逻辑求解器、ASCII 渲染。纯标准库。
"""
import argparse
import random
import sys

FILLED = "██"
EMPTY = "  "
UNKNOWN = "··"


def blocks_of(line):
    """把一行 0/1 序列转成线索块, 如 [1,1,0,1] -> [2,1]; 全空 -> []."""
    out = []
    run = 0
    for v in line:
        if v:
            run += 1
        elif run:
            out.append(run)
            run = 0
    if run:
        out.append(run)
    return out


def clues_from_grid(grid):
    n = len(grid)
    rows = [blocks_of(grid[i]) for i in range(n)]
    cols = [blocks_of([grid[i][j] for i in range(n)]) for j in range(n)]
    return rows, cols


def line_placements(length, blocks, known):
    """返回所有与 known(元素为 None/0/1)一致的行填充方案(0/1 元组列表)."""
    results = []
    if not blocks:
        if all(k in (None, 0) for k in known):
            results.append((0,) * length)
        return results

    def rec(bi, cells):
        if bi == len(blocks):
            cells = cells + [0] * (length - len(cells))
            if all(known[i] is None or known[i] == cells[i] for i in range(length)):
                results.append(tuple(cells))
            return
        b = blocks[bi]
        min_after = sum(blocks[bi + 1:]) + len(blocks[bi + 1:])
        for start in range(len(cells), length - b - min_after + 1):
            cells2 = cells + [0] * (start - len(cells)) + [1] * b
            if bi < len(blocks) - 1:
                cells2.append(0)
            if all(known[i] is None or known[i] == cells2[i] for i in range(len(cells2))):
                rec(bi + 1, cells2)

    rec(0, [])
    return results


def solve(row_clues, col_clues, _depth=0):
    """求解; 返回解网格(0/1)或 None(无解). 逻辑传播 + 猜测回溯."""
    n = len(row_clues)
    known = [[None] * n for _ in range(n)]

    def propagate():
        changed = True
        while changed:
            changed = False
            for i in range(n):
                poss = line_placements(n, row_clues[i], known[i])
                if not poss:
                    return False
                for j in range(n):
                    vals = {p[j] for p in poss}
                    if len(vals) == 1:
                        v = vals.pop()
                        if known[i][j] != v:
                            known[i][j] = v
                            changed = True
            for j in range(n):
                col = [known[i][j] for i in range(n)]
                poss = line_placements(n, col_clues[j], col)
                if not poss:
                    return False
                for i in range(n):
                    vals = {p[i] for p in poss}
                    if len(vals) == 1:
                        v = vals.pop()
                        if known[i][j] != v:
                            known[i][j] = v
                            changed = True
        return True

    if not propagate():
        return None
    # 找未定格
    pick = None
    for i in range(n):
        for j in range(n):
            if known[i][j] is None:
                pick = (i, j)
                break
        if pick:
            break
    if pick is None:
        return [[known[i][j] for j in range(n)] for i in range(n)]
    if _depth > n * n:
        return None
    i, j = pick
    for v in (1, 0):
        trial_rows = [list(r) for r in row_clues]
        trial_cols = [list(c) for c in col_clues]
        sub = _Solver(trial_rows, trial_cols, known, i, j, v, _depth)
        res = sub.run()
        if res is not None:
            return res
    return None


class _Solver:
    """带预设猜测的求解器(避免闭包递归传参混乱)."""

    def __init__(self, row_clues, col_clues, known, gi, gj, gv, depth):
        self.row_clues = row_clues
        self.col_clues = col_clues
        self.n = len(row_clues)
        self.known = [row[:] for row in known]
        self.known[gi][gj] = gv
        self.depth = depth

    def run(self):
        return self._solve_with_preset()

    def _solve_with_preset(self):
        n = self.n
        known = self.known
        row_clues, col_clues = self.row_clues, self.col_clues

        def propagate():
            changed = True
            while changed:
                changed = False
                for i in range(n):
                    poss = line_placements(n, row_clues[i], known[i])
                    if not poss:
                        return False
                    for j in range(n):
                        vals = {p[j] for p in poss}
                        if len(vals) == 1:
                            v = vals.pop()
                            if known[i][j] != v:
                                known[i][j] = v
                                changed = True
                for j in range(n):
                    col = [known[i][j] for i in range(n)]
                    poss = line_placements(n, col_clues[j], col)
                    if not poss:
                        return False
                    for i in range(n):
                        vals = {p[i] for p in poss}
                        if len(vals) == 1:
                            v = vals.pop()
                            if known[i][j] != v:
                                known[i][j] = v
                                changed = True
            return True

        if not propagate():
            return None
        pick = None
        for i in range(n):
            for j in range(n):
                if known[i][j] is None:
                    pick = (i, j)
                    break
            if pick:
                break
        if pick is None:
            return [[known[i][j] for j in range(n)] for i in range(n)]
        if self.depth > n * n:
            return None
        i, j = pick
        for v in (1, 0):
            sub = _Solver(row_clues, col_clues, known, i, j, v, self.depth + 1)
            res = sub.run()
            if res is not None:
                return res
        return None


def generate(size, seed=None, density=0.55):
    """生成点对称随机图案(上半镜像到下半, 保证至少有点内容)."""
    rng = random.Random(seed)
    half = (size + 1) // 2
    grid = [[0] * size for _ in range(size)]
    for i in range(half):
        for j in range(size):
            v = 1 if rng.random() < density else 0
            grid[i][j] = v
            grid[size - 1 - i][j] = v
    # 避免全空或全满
    total = sum(sum(r) for r in grid)
    if total == 0:
        grid[0][0] = grid[size - 1][0] = 1
    elif total == size * size:
        grid[0][0] = grid[size - 1][0] = 0
    return grid


def render_puzzle(row_clues, col_clues, solution=None, show_solution=False):
    n = len(row_clues)
    max_rw = max((len(r) for r in row_clues), default=0)
    max_ch = max((len(c) for c in col_clues), default=0)
    lines = []
    for k in range(max_ch):
        parts = [" " * (max_rw * 3)]
        for j in range(n):
            c = col_clues[j]
            idx = k - (max_ch - len(c))
            parts.append(f"{c[idx]:>2} " if idx >= 0 else "   ")
        lines.append("".join(parts).rstrip())
    for i in range(n):
        r = row_clues[i]
        head = "".join(["   "] * (max_rw - len(r)) + [f"{x:>2} " for x in r])
        if show_solution and solution:
            body = "".join(FILLED if solution[i][j] else EMPTY for j in range(n))
        else:
            body = UNKNOWN * n
        lines.append(head + body)
    return "\n".join(lines)


def puzzle_to_text(row_clues, col_clues):
    n = len(row_clues)

    def enc(clue):
        return " ".join(map(str, clue)) if clue else "0"

    return "\n".join([str(n)] + [enc(r) for r in row_clues] + [enc(c) for c in col_clues]) + "\n"


def puzzle_from_text(text):
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip() != ""]
    n = int(lines[0])

    def dec(s):
        if s.strip() == "0":
            return []
        return [int(x) for x in s.split()]

    rows = [dec(lines[1 + i]) for i in range(n)]
    cols = [dec(lines[1 + n + i]) for i in range(n)]
    return rows, cols


def main(argv=None):
    ap = argparse.ArgumentParser(description="nonogram —— 数织谜题生成与求解(纯标准库)")
    ap.add_argument("--size", type=int, default=5, choices=[5, 10], help="棋盘尺寸(默认 5)")
    ap.add_argument("--seed", type=int, default=None, help="随机种子")
    ap.add_argument("--solve", metavar="FILE", default=None, help="求解文件中的谜题")
    ap.add_argument("--save", metavar="FILE", default=None, help="把生成的谜题存为文本")
    ap.add_argument("--show-solution", action="store_true", help="同时显示答案")
    args = ap.parse_args(argv)

    if args.solve:
        with open(args.solve, encoding="utf-8") as f:
            row_clues, col_clues = puzzle_from_text(f.read())
        sol = solve(row_clues, col_clues)
        if sol is None:
            print("无解: 线索矛盾。")
            return 1
        print(render_puzzle(row_clues, col_clues, sol, show_solution=True))
        return 0

    grid = generate(args.size, args.seed)
    row_clues, col_clues = clues_from_grid(grid)
    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            f.write(puzzle_to_text(row_clues, col_clues))
        print(f"已保存到 {args.save}")
    print(render_puzzle(row_clues, col_clues))
    if args.show_solution:
        print()
        print("答案:")
        print(render_puzzle(row_clues, col_clues, grid, show_solution=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
