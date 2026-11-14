#!/usr/bin/env python3
"""黑箱協議 BLACKBOX PROTOCOL v1 — Python 版
連續採集達 5 次後，接下來 2 個行動禁止採集（COLLECT_STREAK_MAX / COLLECT_BAN）
自動模擬（預設）: python blackbox_protocol.py [局數] [--seed 42] [--noplot] [--nostrat]   （預設 1000 局，圖表直接跳出視窗，不存檔）
手動遊玩:         python blackbox_protocol.py --play
"""
import random, sys, math, re

COLLECT_STREAK_MAX = 5   # 連續採集達此次數後，接下來禁止採集
COLLECT_BAN = 2          # 禁止採集的行動數
STYLE_ORDER = ['資本', '保守', '激進', '操盤', '均衡']   # 「最佳策略」圖表由左至右的風格順序
CHAIN_N = 3             # 連續採集次數
CHAIN_MAX_RES = 10      # 資源需 < 此值，連續採集才有獎勵
CHAIN_BONUS = 2         # 連續採集獎勵資源
HUNT_COUNT_FROM = 3     # 獵殺者命中從第幾回合起計入
HUNT_HITS = 3          # 獵殺者門檻：淘汰 1 人，或成功命中 N 次
ATK_LOSS = 4           # 被攻擊成功時損失的資源
INCITE_USES = 3         # 操盤手「挑撥」次數
FORCE_USES = 1          # 操盤手強制交易次數
EXPLORER_P = .5          # 探勘者：每次探索額外獲得 1 資源的機率
PROPHET_LAST = 5         # 預言家：只能在第幾回合（含）以前進行預測
BROKER_MAX = 3            # 情報商：整局最多賣情報次數
CAP_RPV = 4.5            # 資本家：每幾資源換 1 VP（一般玩家為 RES_PER_VP）
HUNTER_KILL_VP = 3.5     # 獵殺者：每擊殺一人的 VP（一般玩家為 KILL_VP）
DBL_MAX, DBL_EACH = 2, 6.25 # 雙面人：背叛最多計幾次 / 每次背叛的 VP
ABILITY_GOALS = ('strategist', 'broker', 'speculator', 'explorer', 'smuggler', 'prophet')   # 能力型隱藏目標：持有即視為達成，VP 以 GOAL_VP 的基本值計
SMUGGLER_MAX = 4          # 走私客：整局最多走私次數
SMUGGLE_VP = 1.75          # 走私客：每次走私（3 張情報）換得的 VP
SMUGGLER_COST = 1        # （目前未使用）舊版走私客：付幾資源換一張情報
DBL_PLAN_P = .12           # 雙面人 AI 每回合採用「先承諾再背叛」組合的機率
DEFEND_BONUS = 2          # 防禦行動給的防禦加成（基本防禦 3 另計；+2 時防禦中為 5，攻擊 3+備戰2 仍可擊穿）
INFO_VP = 0.3             # 情報值 = 結算時手上持有的情報卡張數；每張換多少 VP（互換、預測不再增加情報值）
CRED_KEEP = 1             # 承諾期滿且沒有背叛：信用 +
GOALS_PER_GAME = 6       # 隱藏目標共 18 種，每局隨機抽出幾種
MERCH_N, TOUGH_N, AVENG_N, HONOR_PROM = 8, 1, 1, 6     # 商人交易次數 / 倖存者被打中次數 / 復仇者反擊次數 / 守約者承諾數
AVENG_COUNTERBACK_AP = 4  # 復仇者：成功反擊「曾攻擊過自己的人」時拿回的資源（名稱沿用舊版，實際是資源不是 AP）
HERMIT_RES, HERMIT_THR = 10, 1                           # 隱士：最終資源 ≥ / 最終威脅 ≤
GAMB_SPENT, GAMB_HITS = 4, 2                            # 賭徒：備戰花費 ≥ / 命中次數 ≥
MANIP_N = 2             # 操盤手需讓幾名玩家出手攻擊
MANIP_TIP = 1           # 操盤手交易/挑撥後，影響持續到第幾回合（普通玩家為 1）
GOAL_VP = {'hunter': 8.5, 'guard': 9.5, 'cap': 7.5, 'manip': 9, 'obs': 8.5, 'honor': 9, 'avenge': 9, 'merch': 8.5, 'tough': 8, 'hermit': 8.5, 'gamble': 9, 'strategist': 7.5, 'broker': 6.5, 'speculator': 7.25, 'explorer': 7, 'smuggler': 5, 'prophet': 7}   # 各目標達成的 VP；能力型目標的數值是「基本 VP」（已依模擬校準）。雙面人不在此表（每次背叛 DBL_EACH VP，最多 DBL_MAX 次）
GUARD_PROG_VP = 0.5      # 守護者：每 1 點守護進度的 VP（成功擋下對被守護者的攻擊 +1 進度）
GUARD_PROG_CAP = 3       # 守護進度最多計幾點
KILL_VP = 3.5            # 每擊殺一名玩家的 VP
GUARD_BONUS = 1         # 守護者防禦時，被守護者防禦加成
GUARD_STACK = False     # 守護加成是否能和被守護者自己的防禦疊加
GUARD_DEF_W = 1.5       # AI 守護者防禦傾向倍率
CAP_DEF_FROM = 99       # 資本家資源 ≥ 此值時自身防禦 +1（99 = 停用）
CAP_BLEND = 0.5         # 資本家目標對 AI 風格權重的混合比例
CAP_PROFILE = [4, 1, 1, 1.5, 1.5, .5]
CAP_GOAL = 15          # 資本家門檻
BROKER_GAIN = 4          # 情報商每賣出一張情報獲得的資源（買方仍付 2）
INFO_VP_OBS = 0.2        # 觀察者：每張持有情報的 VP 權重
INFO_VP_EXPLORER = 0.3  # 探勘者：只計算自己探索或交易取得的情報，每張的 VP 權重
HUNTER_EARLY_BOOST, HUNTER_EARLY_UNTIL = 2, 4   # 獵殺者第 1～4 回合備戰上限 2
HUNTER_HIT_RES = 0       # 獵殺者攻擊成功（未被擋下）獲得的資源
ATK_FAIL_PEN = 0         # 攻擊失敗（被擋下）時，攻擊者下回合少幾 AP
ATK_GAIN = 2             # 攻擊成功（未被擋下）時，攻擊者拿回的資源
BOOST_HUNTER = 1       # 獵殺者備戰（花資源加攻擊）上限
BOOST_MAX = 2          # 其他玩家備戰上限
RES_PER_VP = 4         # 每幾點資源換 1 VP
PROM_ROUNDS = 1        # 承諾持續回合數
ROUNDS = 8
FIXED = ('永遠採集', '永遠攻擊', '永遠背叛', '追星級', '永遠防禦')   # 單一策略測試用（完全不攻擊走一般權重表）
STRATS = ['永遠採集', '永遠攻擊', '永遠背叛', '完全不攻擊', '追星級', '永遠防禦']
AC = ['採集', '探索', '觀察', '交易', '防禦', '攻擊']
COST = [1, 1, 1, 1, 1, 2]
HUNTER_CHEAP_FROM = 5   # 獵殺者從第幾回合起攻擊只花 1AP（第4回合後）
def cost(p, a, r): return 1 if (a == 5 and p.goal == 'hunter' and r >= HUNTER_CHEAP_FROM) else COST[a]
W = {'保守': [1.6, 1, .8, 2.2, .9, 1], '激進': [3.5, 1, .5, 1, 1.5, 2.5], '操盤': [2.2, 2, 1, 3, 1, .9],
     '資本': [1.8, 1.2, 1.2, 1.5, 1, 1.2], '均衡': [2, 1.5, 1, 1.5, 1, 1], '完全不攻擊': [2, 1.5, 1, 1.5, 1, 0]}   # AI 風格行動權重：採集/探索/觀察/交易/防禦/攻擊
GL = {'hunter': ('獵殺者', f'淘汰 1 人，或成功命中（未被擋下，第{HUNT_COUNT_FROM}回合起計）{HUNT_HITS} 次（第{HUNTER_CHEAP_FROM - 1}回合後攻擊只花1AP、第1～{HUNTER_EARLY_UNTIL}回合備戰上限{HUNTER_EARLY_BOOST}、之後{BOOST_HUNTER}' + (f'；攻擊成功 +{HUNTER_HIT_RES} 資源' if HUNTER_HIT_RES else '') + '）'),
      'guard': ('守護者', f'指定玩家活到最後；他每次被攻擊的回合你都必須防禦(並為其防禦+{GUARD_BONUS})；只有他實際被打中且你沒防禦才算失敗'),
      'cap': ('資本家', f'結束時資源 ≥{CAP_GOAL}（能力：每次採集額外+0.5資源）'),
      'manip': ('操盤手', f'{MANIP_N} 名玩家因你的交易/情報而出手攻擊（能力：強制交易{FORCE_USES}次，付3換5，對方不能拒絕；挑撥{INCITE_USES}次，讓對方對你指定的玩家記仇）'),
      'dbl': ('雙面人', '可以背叛口頭承諾'),
      'obs': ('觀察者', '持有 6 張≥3星情報，或 4 張≥4星(含5星)情報')}
GL.update({
    'honor': ('守約者', f'簽下至少 {HONOR_PROM} 份承諾（對方付你資源、你保證不攻擊），且全程沒有背叛過任何一份'),
    'avenge': ('復仇者', f'成功反擊「曾攻擊過你」的玩家至少 {AVENG_N} 次；每次成功反擊拿回 {AVENG_COUNTERBACK_AP} 資源'),
    'merch': ('商人', f'累計進行 {MERCH_N} 次交易行動'),
    'tough': ('倖存者', f'被成功攻擊至少 {TOUGH_N} 次，仍存活到最後'),
    'hermit': ('隱士', f'全程從未攻擊，最終威脅 ≤{HERMIT_THR}、資源 ≥{HERMIT_RES}，且存活'),
    'gamble': ('賭徒', f'累計備戰花費 ≥{GAMB_SPENT} 資源，且成功命中至少 {GAMB_HITS} 次')})
RL = {
    'strategist': ('軍師', '每局一次，回合開始可額外 +1 AP（當回合 4 AP，不可累積；不降低獵殺者攻擊所需 AP）'),
    'broker': ('情報商', f'每回合一次（不耗 AP）把一張情報賣給指定玩家：買方付 2 資源並取得該情報，你獲得 {BROKER_GAIN} 資源、失去該情報；買方可拒絕；整局最多 {BROKER_MAX} 次'),
    'speculator': ('投機者', '第1回合 +1 資源；第5回合只有第 1 次探索 +1 資源；第6回合採集不受減益'),
    'explorer': ('探勘者', f'每次探索有 {EXPLORER_P:.0%} 機率額外獲得 1 資源（不耗 AP）；情報值只計算自己探索或交易取得的情報，每張 {INFO_VP_EXPLORER} VP'),
    'smuggler': ('走私客', f'交易行動多了「走私」選項：把 3 張情報換成 {SMUGGLE_VP} VP，整局最多 {SMUGGLER_MAX} 次'),
    'prophet': ('預言家', f'每回合可預測 2 名不同玩家「本回合」是否攻擊；每猜中 1 名 +1 VP（預言 VP 沒有總上限），猜錯不扣分；第 {PROPHET_LAST} 回合後不能再預測')}
GL.update(RL)      # 這六個（軍師…預言家）和獵殺者、雙面人一樣是隱藏目標，共 18 種，每局隨機抽 GOALS_PER_GAME 種
GL['dbl'] = ('雙面人', f'背叛口頭承諾，最多計 {DBL_MAX} 次，每次 +{DBL_EACH} VP（不必存活；承諾持續{PROM_ROUNDS}回合；背叛信用損失-1）')
GL['hermit'] = ('隱士', f'全程從未攻擊，最終威脅 ≤{HERMIT_THR}、資源 ≥{HERMIT_RES}，且存活')
GL['guard'] = ('守護者', GL['guard'][1] + f'；每成功擋下一次對被守護者的攻擊 +1 守護進度（每點 +{GUARD_PROG_VP} VP，最多 {GUARD_PROG_CAP} 點）；被守護者沒被攻擊也算達成')
GL['cap'] = ('資本家', f'結束時資源 ≥{CAP_GOAL}（能力：每次採集額外+0.5資源；資源換 VP 為每 {CAP_RPV} 資源 1 VP）')
GL['hunter'] = ('獵殺者', GL['hunter'][1] + f'；每擊殺一人 {HUNTER_KILL_VP} VP')
GL['obs'] = ('觀察者', GL['obs'][1] + f'；持有情報每張只算 {INFO_VP_OBS} VP')
ROLE_EN = {'strategist': 'Strategist', 'broker': 'Info broker', 'speculator': 'Speculator', 'explorer': 'Explorer', 'smuggler': 'Smuggler', 'prophet': 'Prophet'}
EV = ['資源繁榮：採集 +1', '情報洩漏：所有人獲得2張公共情報（兩張內容不會相同）', '市場波動：本回合起可淘汰玩家',
      '信任危機：背叛信用損失加重', '黑市：探索時額外獲得 1 張情報（仍只花 1 AP）', '資源短缺：採集收益降低',
      '全面恐慌：所有威脅 +1', '最終結算']
clamp = lambda v, a, b: max(a, min(b, v))
star = lambda n: '★' * n + '☆' * (5 - n)


class P:
    def __init__(s, i, name, sty, goal):
        s.i, s.n, s.sty, s.goal = i, name, sty, goal
        s.res, s.info, s.cred, s.thr = 5, 2, 5, 0
        s.alive, s.dying, s.kills, s.hits, s.manip, s.beti = True, False, 0, 0, 0, 0
        s.cur, s.hh, s.gr = [0] * 6, [], {}
        s.def_, s.tgt, s.pred, s.predOk, s.predN = False, None, None, 0, 0
        s.risk, s.an, s.note, s.atkN = 2, 1, '', 0
        s.tr, s.armed = {}, -9
        s.cards, s.gfail, s.frac, s.mt, s.out, s.ghits = [], 0, 0.0, 0, 0, 0
        s.lch = False                          # 本回合是否真的發動攻擊（承諾取消不算）
        s.cs, s.pen, s.ap, s.inc, s.cc, s.ban = 0, 0, 3, 0, 0, 0     # 連續採集計數 / 下回合AP懲罰 / 本回合AP / 挑撥次數 / 連續採集數 / 禁止採集剩餘行動
        s.pm, s.rev, s.hurt, s.bspent, s.suse = 0, 0, 0, 0, 0       # 承諾數 / 復仇命中 / 被打中次數 / 備戰花費 / 走私次數
        s.gprog = 0                              # 守護進度（成功擋下對被守護者的攻擊）
        s.svp, s.buse, s.sp5 = 0.0, 0, False      # 走私換得的 VP（初始 0）/ 情報商已賣次數 / 投機者第5回合加成已用
        s.role, s.hand, s.stru, s.ruse, s.pvp, s.preds, s.npreds = '', [], False, False, 0, [], []   # 能力判斷用 / 持有情報 / 軍師已用 / 本回合已用能力 / 預言家VP / 預測對象


class Game:
    def __init__(s, human=True, styles=None):
        s.human = human
        names = ['你', 'A', 'B', 'C', 'D', 'E']
        styles = styles or ['人類', '保守', '激進', '操盤', '資本', '均衡']
        goals = random.sample(list(GL), min(GOALS_PER_GAME, len(GL)))      # 18 種隱藏目標隨機抽 6 種
        s.P = [P(i, names[i], styles[i], goals[i]) for i in range(6)]
        for p in s.P:
            if p.goal == 'guard':
                p.tgt = random.choice([q.i for q in s.P if q.i != p.i])
        for p in s.P: p.role = p.goal if p.goal in ABILITY_GOALS else ''      # 能力型隱藏目標的能力判斷用
        s.r, s.intel, s.log = 1, [], []

    # ---------- 工具 ----------
    def alive(s): return [p for p in s.P if p.alive]
    def say(s, t):
        if s.human: print(t)
    def col(s, p=None):
        if p is not None and p.role == 'speculator' and s.r == 6: return 2        # 投機者：資源短缺不受減益
        return 3 if s.r == 1 else 1 if s.r == 6 else 2

    def bcap(s, p):
        if p.goal != 'hunter': return BOOST_MAX
        return HUNTER_EARLY_BOOST if s.r <= HUNTER_EARLY_UNTIL else BOOST_HUNTER

    def new_intel(s, p, src='explore'):
        alive = s.alive()
        if not alive: return None
        ai = [q for q in alive if q is not p] or alive
        def make():
            a = random.choice(ai); k = random.choice('gyyrr')
            fact = lambda: (1, 5, f'{a.n} 目前資源至少 {a.res // 2 * 2}')
            if k == 'g': return fact()
            if k == 'y':
                pl = [(i, x) for i, v in s.plans.items() for x in v if x[0] == 5 and s.P[i].alive]
                if pl and random.random() < .7:
                    i, x = random.choice(pl); return (2, random.choice([3, 4]), f'{s.P[i].n} 可能準備攻擊 {s.P[x[1]].n}')
                oth = [q for q in alive if q is not a]
                return (2, random.choice([3, 3, 4]), f'{a.n} 可能準備攻擊 {random.choice(oth).n}') if oth else fact()     # 避免「A 攻擊 A」
            oth = [q for q in alive if q is not a]
            return (3, random.choice([1, 2, 3]), f'{a.n} 正在與 {random.choice(oth).n} 合作') if oth else fact()
        for _ in range(40):                                                  # 同一回合、同一玩家手上不得有內容完全相同的情報
            c = make()
            if all(x[2] != c[2] for x in p.hand if x[3] == s.r): break
        c = c + (s.r, src)                                                       # 內部記錄取得回合（畫面上不再顯示「過時」）
        p.info += 1; p.cards.append(c[1]); p.hand.append(c)
        if p.i == 0: s.intel.insert(0, c)
        return c

    def can_receive(s, q, c):
        """買方手上已有同回合、內容完全相同的情報時，不接受重複的卡"""
        return not any(x[2] == c[2] and x[3] == c[3] for x in q.hand)

    def transfer(s, a, b, c):
        """情報商：把情報卡 c 從 a 轉給 b"""
        if c in a.hand: a.hand.remove(c)
        if c[1] in a.cards: a.cards.remove(c[1])
        if a.i == 0 and c in s.intel: s.intel.remove(c)
        c2 = c[:4] + ('buy',)                                              # 買來的情報：來源標記為 buy
        b.hand.append(c2); b.cards.append(c2[1])
        if b.i == 0: s.intel.insert(0, c2)

    def smuggle(s, p):
        """走私客：把持有的 3 張情報（星級最低的）換成 SMUGGLE_VP"""
        for c in sorted(p.hand, key=lambda c: c[1])[:3]:
            p.hand.remove(c)
            if c[1] in p.cards: p.cards.remove(c[1])
            if p.i == 0 and c in s.intel: s.intel.remove(c)
        p.suse += 1; p.svp += SMUGGLE_VP

    def ai_roles(s):
        """AI 的不耗 AP 角色能力（情報商）"""
        for p in s.alive():
            if (p.i == 0 and s.human) or p.ruse: continue
            if p.role == 'broker' and p.buse < BROKER_MAX and p.hand and random.random() < .7:
                bs = [q for q in s.alive() if q is not p and q.res >= 2]
                if not bs: continue
                q = random.choice(bs); cs = [c for c in p.hand if s.can_receive(q, c)]
                if not cs: continue
                c = random.choice(cs)
                if q.i == 0 and s.human: s.ioffers.append((p.i, c)); p.ruse = True
                elif random.random() < .5: s.transfer(p, q, c); q.res -= 2; p.res += BROKER_GAIN; p.ruse = True; p.buse += 1

    # ---------- AI 計畫 ----------
    def fixed_plan(s, p):
        c = [q for q in s.alive() if q is not p and not (p.goal == 'guard' and q.i == p.tgt)] or [q for q in s.alive() if q is not p]
        if not c: return [(0, None, 0)] * p.ap
        k, ac = p.sty, cost(p, 5, s.r)
        bst = lambda: min(s.bcap(p), (p.res - 1) // 2) if p.res >= 3 else 0
        if k == '永遠採集':
            out, cc, ban = [], p.cc, p.ban
            for _ in range(p.ap):
                if ban > 0: out.append((4, None, 0)); ban -= 1
                else:
                    out.append((0, None, 0)); cc += 1
                    if cc >= COLLECT_STREAK_MAX: cc, ban = 0, COLLECT_BAN
            return out
        if k == '永遠防禦': return [(4, None, 0)] * p.ap
        wt = lambda q: 1 + q.res * .6 + q.thr * .4 + p.gr.get(q.i, 0) * 3 + (2 if q.dying else 0)
        t = max(c, key=lambda q: s.risk(q, p)) if k == '追星級' else random.choices(c, [wt(q) for q in c])[0]
        out, ap = [], p.ap
        if k == '永遠背叛': out.append((3, t.i, 0)); ap -= 1      # 先簽承諾，再攻擊同一人
        while ap >= ac: out.append((5, t.i, bst())); ap -= ac
        return out + [(0, None, 0)] * ap

    def plan(s, p):
        if p.sty in FIXED: return s.fixed_plan(p)
        w0 = W.get(p.sty, W['均衡'])[:]
        if p.goal == 'hunter': w0[5] *= 2
        if p.goal == 'dbl': w0[3] *= 3; w0[5] *= 1.5
        if p.goal == 'manip': w0[3] *= 1.4; w0[1] *= 1.2
        if p.goal == 'guard': w0[4] *= GUARD_DEF_W
        if p.goal == 'cap': w0 = [(1 - CAP_BLEND) * x + CAP_BLEND * y for x, y in zip(w0, CAP_PROFILE)]   # 資本家目標讓行動偏向囤資源，降低 AI 風格造成的差異
        if p.goal == 'obs': w0[1] *= 2
        if p.goal == 'honor': w0[3] *= 2.5
        if p.goal == 'avenge': w0[5] *= 1.5
        if p.goal == 'merch': w0[3] *= 3
        if p.goal == 'tough': w0[4] *= .4
        if p.goal == 'hermit': w0[5] = 0; w0[0] *= 1.3
        if p.goal == 'gamble': w0[5] *= 1.5
        if p.goal == 'explorer': w0[1] *= 2.5
        if p.goal == 'smuggler': w0[1] *= 2.5; w0[3] *= 2.5
        if p.goal == 'dbl' and p.beti < DBL_MAX and s.r >= 2 and p.ap >= 1 + cost(p, 5, s.r) and random.random() < DBL_PLAN_P:
            c = [q for q in s.alive() if q is not p]                          # 雙面人 AI：先對同一人簽承諾（交易），再攻擊他 = 背叛
            if c:
                t = random.choice(c).i; b = min(BOOST_MAX, (p.res - 1) // 2) if p.res >= 3 else 0
                out = [(3, t, 0), (5, t, b)]; ap = p.ap - 1 - cost(p, 5, s.r)
                return out + [(0, None, 0)] * ap if p.ban == 0 else out + [(4, None, 0)] * ap
        ap, out, cc, ban = p.ap, [], p.cc, p.ban
        while ap > 0:
            w = w0[:]
            if ban > 0: w[0] = 0
            if ap < cost(p, 5, s.r): w[5] = 0
            if s.r == 1: w[5] *= .5
            a = random.choices(range(6), w)[0]; t = None
            if a in (2, 3, 5):
                c = [q for q in s.alive() if q is not p and not (a == 5 and p.goal == 'guard' and q.i == p.tgt)]
                if not c: a = 0
                else:
                    ws = [1 + q.res * .6 + q.thr * .4 + p.gr.get(q.i, 0) * (6 if p.goal == 'avenge' else 3) + (4 if s.warn and q.res >= 12 else 0) + (2 if q.dying else 0) + (4 if q.dying and p.goal == 'hunter' else 0) if a == 5 else 1 + q.cred * .3 for q in c]
                    t = random.choices(c, ws)[0].i
                    if p.goal == 'dbl' and a == 5:           # 雙面人：先交易(承諾)，再攻擊同一人
                        prev = [x[1] for x in out if x[0] == 3 and x[1] is not None and s.P[x[1]].alive]
                        if prev: t = prev[0]
            if a == 0 and ban > 0: a = random.choice((1, 4))      # 禁止採集時改為探索或防禦
            if a == 0:
                cc += 1
                if cc >= COLLECT_STREAK_MAX: cc, ban = 0, COLLECT_BAN
            else: cc, ban = 0, max(0, ban - 1)
            b = 0
            if a == 5 and p.res >= 3 and random.random() < (.9 if p.goal in ('hunter', 'gamble') or p.sty == '激進' else .6): b = min(s.bcap(p), (p.res - 1) // 2)
            out.append((a, t, b)); ap -= cost(p, a, s.r)
        return out

    # ---------- 評估 ----------
    def risk(s, p, v):
        """p 對 v 的威脅估計：近期攻擊、報復、備戰、處境、與 v 的互動，加上噪音"""
        ra = sum(h[5] for h in p.hh[-2:])
        z = (1 + ra * .6 + p.thr * .12 + p.gr.get(v.i, 0) * .5 + (p.an - 1) * .5
             + (.7 if p.armed >= s.r - 1 else 0) + (.8 if p.res <= 3 and v.res >= 6 else 0)
             + (.3 if v.res >= p.res + 4 else 0) - (.9 if p.tr.get(v.i, -9) >= s.r - 2 else 0)
             - (.3 if p.hh and p.hh[-1][4] else 0) + random.uniform(-.7, .7))
        return clamp(round(z), 1, 5)

    def anom(s, p):
        H = p.hh
        if len(H) < 2: return 1
        l, pv = H[-1], H[:-1]
        d = math.sqrt(sum((l[k] - sum(h[k] for h in pv) / len(pv)) ** 2 for k in range(6)))
        return 3 if d > 2.4 else 2 if d > 1.6 else 1

    # ---------- 回合 ----------
    def start_round(s):
        s.atks, s.offers, s.ioffers = [], [], []
        for (a, t), v in getattr(s, 'prom', {}).items():                 # 承諾期滿且沒有背叛（背叛會刪除承諾）→ 守約者信用 +
            if v < s.r:
                s.P[a].cred = min(10, s.P[a].cred + CRED_KEEP)
                if a == 0 and s.human: s.say(f'🤝 你對 {s.P[t].n} 的承諾期滿且守約：信用 +{CRED_KEEP}')
        s.prom = {k: v for k, v in getattr(s, 'prom', {}).items() if v >= s.r}
        s.tips = [x for x in getattr(s, 'tips', []) if x[2] >= s.r]
        for p in s.P: p.cur, p.def_, p.ap, p.pen, p.lch, p.ruse = [0] * 6, False, max(1, 3 - p.pen), 0, False, False
        for p in s.alive():
            if p.role == 'speculator' and s.r == 1: p.res += 1                       # 投機者：資源繁榮 +1
            if p.role == 'strategist' and not p.stru and not (p.i == 0 and s.human) and (s.r == 6 or (s.r >= 3 and random.random() < .25)):
                p.ap += 1; p.stru = True                                           # AI 軍師：挑回合使用額外 AP
        s.warn = any(p.res >= 12 for p in s.alive())
        s.plans = {p.i: s.plan(p) for p in s.alive() if (p.i or not s.human)}
        for p in s.P:
            p.an = s.anom(p)
            p.risk = s.risk(p, s.P[0])
        for p in s.alive():
            if p.i or not s.human: p.preds = s.make_preds(p)             # AI 在本回合開始時預測
        if s.r == 2:
            for p in s.alive(): s.new_intel(p, 'event'); s.new_intel(p, 'event')               # 與事件文字一致：2 張
        s.say(f'\n══════ 第 {s.r}/{ROUNDS} 回合 ══════\n📰 {EV[s.r - 1]}')
        if s.warn: s.say('🚨 全體警示：場上有玩家資源 ≥12！')
        if s.human and s.P[0].ap < 3 and s.P[0].alive: s.say(f'⚠ 上回合攻擊失敗，本回合 AP 只有 {s.P[0].ap}')

    def do(s, p, a, t=None, b=0):
        if a == 0 and p.ban > 0: a = random.choice((1, 4))      # 採集禁止期間（安全網）：改為探索或防禦
        p.cur[a] += 1
        if a != 0: p.cs = 0; p.cc = 0; p.ban = max(0, p.ban - 1)
        else:
            p.cc += 1                                         # 連續採集計數；達上限後禁止採集
            if p.cc >= COLLECT_STREAK_MAX: p.cc = 0; p.ban = COLLECT_BAN
        if a == 0:
            g = s.col(p)
            if p.res >= 17: p.frac += .5; g = 0; p.thr = clamp(p.thr + 3, 0, 10)
            elif p.res >= 12: g = 1; p.thr = clamp(p.thr + 1, 0, 10)
            if p.goal == 'cap': p.frac += .5          # 資本家能力：每次採集額外 +0.5
            k = int(p.frac); p.frac -= k
            p.cs = min(p.cs + 1, CHAIN_N); bonus = 0
            if p.cs >= CHAIN_N and p.res < CHAIN_MAX_RES:
                p.cs = 0; bonus = CHAIN_BONUS
                if p.i == 0: s.say(f'✨ 資源<{CHAIN_MAX_RES} 且連續採集{CHAIN_N}次，額外 +{CHAIN_BONUS} 資源')
            p.res += g + k + bonus
        elif a == 1:
            s.new_intel(p)
            if p.role == 'explorer' and random.random() < EXPLORER_P: p.res += 1       # 探勘者：機率額外 +1 資源
            if p.role == 'speculator' and s.r == 5 and not p.sp5: p.res += 1; p.sp5 = True    # 投機者：黑市只有第 1 次探索 +1 資源
            if s.r == 5: s.new_intel(p)                                              # 黑市：不花資源，額外 +1 張情報
        elif a == 3 and t is not None:
            q = s.P[t]
            if p.i == 0 and s.human: return
            if p.role == 'smuggler' and p.suse < SMUGGLER_MAX and len(p.hand) >= 3: s.smuggle(p); return      # AI 走私客：交易時走私
            p.tr[t] = q.tr[p.i] = s.r
            if p.goal == 'manip' and p.mt < FORCE_USES and p.res >= 3 and q.res >= 2 and random.random() < .6:
                s.force_trade(p, q); s.tips.append((p.i, t, s.r + (MANIP_TIP if p.goal == 'manip' else 1)))
                s.say(f'🔁 {p.n} 對 {q.n} 發動強制交易（付3換5，無法拒絕）'); return
            if q.i == 0 and s.human: s.offers.append(p.i); return
            if p.goal == 'manip' and p.inc < INCITE_USES and random.random() < .12:
                vs = [x for x in s.alive() if x is not p and x is not q]
                if vs:
                    v = random.choice(vs); q.gr[v.i] = q.gr.get(v.i, 0) + 2; p.inc += 1
                    s.tips.append((p.i, t, s.r + MANIP_TIP)); return
            if random.random() < (.95 if p.goal == 'dbl' or p.sty == '永遠背叛' else .8 if p.goal == 'honor' else .5):  # 承諾交易：q 付 1 資源換 p 本回合不攻擊 q
                if q.res >= 1 and random.random() < .5 + p.cred * .04 + (.1 if p.goal == 'dbl' else 0):
                    q.res -= 1; p.res += 1; p.pm += 1; s.prom[(p.i, t)] = s.r + PROM_ROUNDS - 1
            else:
                s.tips.append((p.i, t, s.r + (MANIP_TIP if p.goal == 'manip' else 1)))
                if p.res >= 1: p.res -= 1; q.res += 1; s.new_intel(p, 'trade')               # 公平交易：不再有免費的資訊互換
        elif a == 4: p.def_ = True
        elif a == 5 and t is not None:
            b = min(b, p.res); p.res -= b; p.bspent += b
            if b: p.armed = s.r
            s.atks.append((p.i, t, b))

    def force_trade(s, p, q):
        p.res += 2; q.res -= 2; p.mt += 1      # 操盤手付 3 換 5：淨 +2，對方淨 -2

    def human_trade(s, p, t):
        q = s.P[t]; p.tr[t] = q.tr[0] = s.r
        print(f'  1) 公平交易：你 -1 資源 +1 情報；{q.n} +1 資源\n  2) 承諾交易：{q.n} 付你 1 資源，你保證本回合不攻擊 {q.n}（之後攻擊 = 背叛）')
        can = p.goal == 'manip' and p.mt < FORCE_USES and p.res >= 3 and q.res >= 2
        if can: print(f'  3) 強制交易（操盤手能力，剩 {FORCE_USES - p.mt} 次）：你付 3 資源換 {q.n} 的 5 資源，對方不能拒絕')
        can4 = p.goal == 'manip' and p.inc < INCITE_USES
        if can4: print(f'  4) 挑撥（操盤手能力，剩 {INCITE_USES - p.inc} 次）：讓 {q.n} 對你指定的另一名玩家記仇，更可能攻擊他')
        can5 = p.role == 'smuggler' and p.suse < SMUGGLER_MAX and len(p.hand) >= 3
        if can5: print(f'  5) 走私（走私客能力，剩 {SMUGGLER_MAX - p.suse} 次）：把持有的 3 張情報換成 {SMUGGLE_VP} VP（目前 {len(p.hand)} 張）')
        c = input('  選擇 [1/2' + ('/3' if can else '') + ('/4' if can4 else '') + ('/5' if can5 else '') + ']: ').strip(); s.tips.append((0, t, s.r + (MANIP_TIP if p.goal == 'manip' else 1)))
        if c == '5' and can5:
            s.smuggle(p); print(f'  走私成功：3 張情報 → +{SMUGGLE_VP} VP（剩 {SMUGGLER_MAX - p.suse} 次）'); return
        if c == '4' and can4:
            v = s.pick('  挑撥誰？')
            if v == t: print('  不能挑撥對方自己'); return
            q.gr[v] = q.gr.get(v, 0) + 2; p.inc += 1
            print(f'  你向 {q.n} 散布了關於 {s.P[v].n} 的話術（剩 {INCITE_USES - p.inc} 次）'); return
        if c == '3' and can:
            s.force_trade(p, q); print(f'  強制交易成功：你淨 +2 資源，{q.n} 淨 -2（剩 {FORCE_USES - p.mt} 次）'); return
        if c == '2':
            if q.res >= 1 and random.random() < .5 + p.cred * .04 + (.1 if p.thr >= 3 else 0) + (.1 if p.goal == 'dbl' else 0):
                q.res -= 1; p.res += 1; p.pm += 1; s.prom[(0, t)] = s.r + PROM_ROUNDS - 1; print(f'  {q.n} 接受了，付你 1 資源。你已承諾不攻擊 {q.n}')
            else: print(f'  {q.n} 不相信你的承諾')
        elif p.res >= 1: p.res -= 1; q.res += 1; s.new_intel(p, 'trade'); print('  交易完成，獲得一張情報')
        else: print('  資源不足（需要 1），公平交易取消，不消耗 AP'); return False

    def handle_offers(s):
        for i in s.offers:
            q, m = s.P[i], s.P[0]
            if not m.alive or m.res < 1 or not q.alive: continue
            if input(f'\n📨 {q.n} 提議：你付 1 資源，{q.n} 保證本回合不攻擊你。接受？[y/N] ').strip().lower() == 'y':
                m.res -= 1; q.res += 1; q.pm += 1; s.prom[(i, 0)] = s.r + PROM_ROUNDS - 1; print('  已成交（對方可能遵守，也可能背叛）')

    def resolve(s):
        random.shuffle(s.atks); done = set(); gdone = set()
        for a, t, b in s.atks:
            A, T = s.P[a], s.P[t]
            if not A.alive or not T.alive: continue
            if (a, t) in s.prom:                           # 這次攻擊違反承諾？
                pb = 0 if A.goal == 'honor' else 1.0 if A.sty == '永遠背叛' else .8 if A.goal == 'dbl' else {'激進': .5, '操盤': .4}.get(A.sty, .15)
                if (a or not s.human) and random.random() > pb:
                    s.say(f'🤝 {A.n} 遵守承諾，取消攻擊 {T.n}'); A.cur[5] -= 1; A.res += b; continue
                d = (3 if s.r == 4 else 2) - (1 if A.goal == 'dbl' else 0); A.cred = max(0, A.cred - d); A.beti += 1; A.thr = clamp(A.thr + 1, 0, 10)
                T.gr[a] = T.gr.get(a, 0) + 2; s.prom.pop((a, t), None)
                s.say(f'🗡 {A.n} 背叛了對 {T.n} 的承諾！（{A.n} 信用 -{d}）')
            A.lch = True; A.atkN += 1; T.gr[a] = T.gr.get(a, 0) + 1
            warned = a in T.preds
            gb = 0; miss = []; covers = []
            for G in s.P:
                if G.goal == 'guard' and G.tgt == t and G.alive and G is not A:
                    if G.cur[4] > 0: gb = GUARD_BONUS; covers.append(G)
                    elif (G.i, s.r) not in gdone: miss.append(G)
            av = 3 + b
            dv = 3 + (DEFEND_BONUS if T.def_ else 0) + (1 if warned else 0) + (gb if (GUARD_STACK or not T.def_) else 0) + (1 if T.goal == 'cap' and T.res >= CAP_DEF_FROM else 0)
            for tp, td, _ in s.tips:
                if td == a and (tp, td) not in done: done.add((tp, td)); s.P[tp].manip += 1
            if av >= dv:
                A.hits += 1
                A.res += ATK_GAIN                                                 # 攻擊成功：攻擊者拿回資源
                if A.goal == 'hunter': A.res += HUNTER_HIT_RES                      # 獵殺者攻擊成功 +資源
                if s.r >= HUNT_COUNT_FROM: A.ghits += 1
                T.hurt += 1
                if A.goal == 'avenge' and A.gr.get(t, 0) > 0:      # 反擊曾攻擊過自己的人：計數並拿回資源（只限復仇者）
                    A.rev += 1; A.res += AVENG_COUNTERBACK_AP
                for G in miss:
                    if (G.i, s.r) not in gdone: gdone.add((G.i, s.r)); G.gfail += 1
                if s.r <= 2: T.res = max(1, T.res - ATK_LOSS)
                elif T.dying: T.alive = False; T.out = s.r; A.kills += 1; s.say(f'💀 {A.n} 淘汰了 {T.n}')
                else:
                    T.res -= ATK_LOSS
                    if T.res <= 0: T.res, T.dying = 0, True
                if T.alive: s.say(f'⚔ {A.n} 攻擊 {T.n} 成功（攻{av}≥防{dv}）{"(瀕死)" if T.dying else ""}')
            else:
                A.pen = ATK_FAIL_PEN
                for G in covers: G.gprog += 1                  # 守護者成功擋下對被守護者的攻擊
                s.say(f'🛡 {A.n} 攻擊 {T.n} 失敗（防{dv}>攻{av}）{"，預警生效" if warned else ""}')

    def make_preds(s, p):
        """AI 預測本回合誰會攻擊（只用公開行為，不看別人的計畫）"""
        k = 2 if p.role == 'prophet' else 1
        lim = PROPHET_LAST if p.role == 'prophet' else ROUNDS
        if s.r > lim: return []
        c = sorted([q for q in s.alive() if q is not p], key=lambda q: -(sum(h[5] for h in q.hh[-2:]) + q.thr * .2 + p.gr.get(q.i, 0) * .5 + random.random() * 1.5))
        return [q.i for q in c[:k]]

    def end_round(s):
        for p in s.alive():                                              # 結算「本回合」的預測
            hit = 0
            for pt in p.preds:
                p.predN += 1
                if s.P[pt].lch:                                          # 只算「真的發動」的攻擊
                    if p.role == 'prophet':
                        if hit < 2:
                            hit += 1; p.pvp += 1
                            if p.i == 0: s.say(f'🎯 預言成功：{s.P[pt].n} 本回合確實發動了攻擊！+1 VP')
                    else:
                        p.predOk += 1
                        if p.i == 0: s.say('🎯 預測正確！+1 VP' if p.predOk <= 4 else '🎯 預測正確（預測 VP 已達上限 4，不再加分）')
        for p in s.P: p.preds, p.npreds = [], []
        if s.r == ROUNDS:                                                # 遊戲結束：仍未到期的承諾視為守約
            for (a, t), v in list(s.prom.items()): s.P[a].cred = min(10, s.P[a].cred + CRED_KEEP)
        for p in s.P:
            p.hh.append(p.cur[:])
            p.thr = clamp(p.thr + 2 * p.cur[5] - (0 if p.cur[5] else 1) + (1 if s.r == 7 else 0), 0, 10)
        s.r += 1

    # ---------- 結算 ----------
    def progress(s, p):
        n = lambda k: sum(x >= k for x in p.cards)
        return {'hunter': f'命中 {p.ghits}/{HUNT_HITS}（擊殺 {p.kills}）', 'guard': f'守護失敗 {p.gfail} 次（需 0 次），守護進度 {min(p.gprog, GUARD_PROG_CAP)}/{GUARD_PROG_CAP}',
                'cap': f'資源 {p.res}/{CAP_GOAL}', 'manip': f'影響攻擊 {p.manip}/{MANIP_N}，挑撥剩 {INCITE_USES - p.inc} 次',
                'dbl': f'背叛 {min(p.beti, DBL_MAX)}/{DBL_MAX}（每次 +{DBL_EACH} VP）',
                'honor': f'承諾 {p.pm}/{HONOR_PROM}，背叛 {p.beti} 次（需 0）', 'avenge': f'反擊 {p.rev}/{AVENG_N}', 'merch': f'交易 {sum(h[3] for h in p.hh) + p.cur[3]}/{MERCH_N}',
                'tough': f'被打中 {p.hurt}/{TOUGH_N}', 'hermit': f'已攻擊 {p.atkN} 次（需 0）、威脅 {p.thr}（需≤{HERMIT_THR}）、資源 {p.res}（需≥{HERMIT_RES}）',
                'gamble': f'備戰花費 {p.bspent}/{GAMB_SPENT}、命中 {p.hits}/{GAMB_HITS}',
                'strategist': '額外 AP ' + ('已使用' if p.stru else '尚未使用'), 'broker': f'已賣情報 {p.buse}/{BROKER_MAX}', 'speculator': '依事件多得資源',
                'explorer': f'探索有 {EXPLORER_P:.0%} 機率 +1 資源', 'smuggler': f'走私 {p.suse}/{SMUGGLER_MAX}（持有情報 {len(p.hand)} 張，需 3 張）', 'prophet': f'預言得分 {p.pvp} VP', 'obs': f'≥3星 {n(3)}/6 或 ≥4星 {n(4)}/4'}[p.goal]

    def goal_ok(s, p):
        g = p.goal
        return {'hunter': p.kills >= 1 or p.ghits >= HUNT_HITS, 'guard': p.tgt is not None and s.P[p.tgt].alive and p.gfail == 0,
                'cap': p.res >= CAP_GOAL, 'manip': p.manip >= MANIP_N, 'dbl': p.beti >= 2,
                'honor': p.pm >= HONOR_PROM and p.beti == 0, 'avenge': p.rev >= AVENG_N, 'merch': sum(h[3] for h in p.hh) >= MERCH_N,
                'tough': p.alive and p.hurt >= TOUGH_N, 'hermit': p.alive and p.atkN == 0 and p.thr <= HERMIT_THR and p.res >= HERMIT_RES,
                'gamble': p.bspent >= GAMB_SPENT and p.hits >= GAMB_HITS,
                'strategist': True, 'broker': True, 'speculator': True, 'explorer': True, 'smuggler': True, 'prophet': True, 'obs': sum(x >= 3 for x in p.cards) >= 6 or sum(x >= 4 for x in p.cards) >= 4}[g]

    def info_vp(s, p):
        if p.goal == 'obs': return len(p.hand) * INFO_VP_OBS
        if p.goal == 'explorer': return sum(1 for c in p.hand if c[4] in ('explore', 'trade')) * INFO_VP_EXPLORER
        return len(p.hand) * INFO_VP

    def vp_raw(s, p):
        rpv = CAP_RPV if p.goal == 'cap' else RES_PER_VP
        kv = HUNTER_KILL_VP if p.goal == 'hunter' else KILL_VP
        gv = min(p.beti, DBL_MAX) * DBL_EACH if p.goal == 'dbl' else (GOAL_VP.get(p.goal, 8) if s.goal_ok(p) else 0)
        if p.goal == 'guard' and s.goal_ok(p): gv += min(p.gprog, GUARD_PROG_CAP) * GUARD_PROG_VP
        return (5 if p.alive else 0) + int(p.res // rpv) + p.kills * kv + gv + min(4, p.predOk) + p.pvp + p.svp + s.info_vp(p)

    def vp(s, p): return int(math.floor(s.vp_raw(p) + .5))              # 結算 VP 四捨五入（0.5 進位）

    def ranking(s): return sorted(s.P, key=lambda p: (s.vp(p), p.res, p.cred), reverse=True)

    # ---------- 人類介面 ----------
    def show(s):
        m = s.P[0]
        print(f'\n【我】資源{m.res} 情報{len(m.hand)} 信用{m.cred} 威脅{m.thr} {"⚠瀕死" if m.dying else ""}{f" ⛔採集禁止中(剩{m.ban}個行動)" if m.ban else ""}')
        print(f'秘密目標：{GL[m.goal][0]} — {GL[m.goal][1]}' + (f'（守護 {s.P[m.tgt].n}）' if m.goal == 'guard' else ''))
        print('目標進度：' + s.progress(m))
        print('── 玩家風險（系統估計，非預言）──')
        for p in s.P[1:]:
            st = '💀已淘汰' if not p.alive else star(p.risk) + (' ⚠瀕死' if p.dying else '') + (f' ⚠行為異常{"高" if p.an == 3 else "中"}' if p.an >= 2 else '')
            print(f' {p.n}: {st}  {p.note}')
        for c in s.intel[:5]: print(f' [{"綠黃紅"[c[0] - 1]}] {c[2]} {star(c[1])}')

    def pick(s, prompt):
        c = [q for q in s.alive() if q.i]
        while True:
            x = input(f'{prompt} ({"/".join(q.n for q in c)}): ').strip().upper()
            for q in c:
                if q.n == x: return q.i
            print('  請輸入有效玩家')

    def human_turn(s):
        m = s.P[0]
        if m.alive and m.role == 'strategist' and not m.stru and input('軍師：本局一次，是否使用額外 +1 AP？[y/N] ').strip().lower() == 'y': m.ap += 1; m.stru = True; print('  本回合 AP +1')
        ap = m.ap
        while ap > 0 and m.alive:
            s.show()
            print(f'\n防禦+{DEFEND_BONUS}；攻擊可備戰；預測本回合會攻擊你的人，他真的打你時你防禦+1\nAP {ap} | 1採集 2探索 3觀察 4交易 5防禦 6攻擊({cost(m, 5, s.r)}AP){" 7" + RL[m.role][0] + "能力(不耗AP)" if m.role == "broker" else ""} 0結束行動')
            c = input('> ').strip()
            if c == '0': break
            if c == '7': s.human_role(m); continue
            if c not in '123456' or len(c) != 1: continue
            a = int(c) - 1
            if a == 0 and m.ban > 0: print(f'  ⛔ 連續採集 {COLLECT_STREAK_MAX} 次後，接下來 {m.ban} 個行動不能採集'); continue
            if cost(m, a, s.r) > ap: print('AP 不足'); continue
            t = s.pick('目標') if a in (2, 3, 5) else None
            b = 0
            if a == 5:
                if (0, t) in s.prom and input(f'  ⚠ 你承諾過不攻擊 {s.P[t].n}，攻擊視為背叛（信用↓）。確定？[y/N] ').lower() != 'y': continue
                b = clamp(int(input(f'  備戰：花資源 +攻擊 (0~{min(s.bcap(m), m.res)}): ') or 0), 0, min(s.bcap(m), m.res))
            if a == 3:
                if s.human_trade(m, t) is False: continue
                m.cur[3] += 1; m.cs = 0; m.cc = 0; m.ban = max(0, m.ban - 1)
            else: s.do(m, a, t, b)
            if a == 2:
                q = s.P[t]; lv = '低' if q.res <= 3 else '中' if q.res <= 6 else '高'
                last = AC[q.hh[-1].index(max(q.hh[-1]))] if q.hh else '—'
                q.note = f'資源{lv} 威脅{q.thr} 近期:{last}' + (' 有備戰跡象' if q.armed >= s.r - 1 else '')
            ap -= cost(m, a, s.r)
        if m.alive and m.role == 'prophet' and s.r > PROPHET_LAST:
            if s.r == PROPHET_LAST + 1: print(f'（預言家第 {PROPHET_LAST} 回合後不能再預測）')
        elif m.alive:
            k = 2 if m.role == 'prophet' else 1
            x = input(f'預測【本回合】誰會發動攻擊？{"可選 2 名，用逗號分隔，" if k == 2 else ""}(輸入玩家字母，直接 Enter 跳過): ').strip().upper().replace(' ', ',')
            m.preds = []
            for y in [y for y in x.split(',') if y]:
                q = next((q for q in s.alive() if q.n == y and q.i), None)
                if q and q.i not in m.preds and len(m.preds) < k: m.preds.append(q.i)

    def human_role(s, m):
        if m.ruse: print('  本回合已使用過角色能力'); return
        if m.role == 'broker' and m.buse >= BROKER_MAX: print(f'  情報商次數已用完（整局最多 {BROKER_MAX} 次）'); return
        if m.role == 'smuggler': print('  走私客的「走私」在【交易】行動的選單裡（選 4 交易 → 5 走私）'); return
        elif m.role == 'broker':
            if not s.intel: print('  你沒有情報可賣'); return
            for i, c in enumerate(s.intel[:8]): print(f'   {i + 1}. [{"綠黃紅"[c[0] - 1]}] {c[2]} {star(c[1])}')
            try: c = s.intel[int(input('  賣哪一張？(編號): ')) - 1]
            except Exception: print('  取消'); return
            q = s.P[s.pick('賣給誰')]
            if not s.can_receive(q, c): print(f'  {q.n} 手上已有同樣的情報，不需要重複購買'); return
            if q.res >= 2 and random.random() < .6:
                s.transfer(m, q, c); q.res -= 2; m.res += BROKER_GAIN; m.ruse = True; m.buse += 1; print(f'  {q.n} 買下了這張情報：你 +{BROKER_GAIN} 資源')
            else: print(f'  {q.n} 拒絕了（或付不起 2 資源）')
        else: print('  你的角色沒有需要手動使用的能力')

    def handle_intel_offers(s):
        m = s.P[0]
        for i, c in s.ioffers:
            q = s.P[i]
            if not m.alive or m.res < 2 or not q.alive: continue
            if input(f'\n📨 情報商 {q.n} 想賣你一張情報：[{"綠黃紅"[c[0] - 1]}] {c[2]} {star(c[1])}，付 2 資源？[y/N] ').strip().lower() == 'y':
                s.transfer(q, m, c); m.res -= 2; q.res += BROKER_GAIN; q.buse += 1; print('  已成交')

    def play_round(s):
        s.start_round()
        if s.human and s.P[0].alive: s.human_turn()
        s.ai_roles()
        for p in s.alive():
            if p.i == 0 and s.human: continue
            for a, t, b in s.plans.get(p.i, []): s.do(p, a, t, b)
        if s.human: s.handle_offers(); s.handle_intel_offers()
        s.resolve(); s.end_round()

    def run(s):
        while s.r <= ROUNDS: s.play_round()
        return s.ranking()


def play():
    g = Game(True); rk = g.run()
    print('\n══════ 最終結算 ══════')
    for i, p in enumerate(rk, 1):
        print(f'{i}. {p.n}({p.sty}) {g.vp(p)}VP  目標:{GL[p.goal][0]}{"✔" if g.goal_ok(p) else "✘"} {"" if p.alive else "💀"}')
    m = g.P[0]
    print('\n你的行動：' + '，'.join(f'{AC[k]}{sum(h[k] for h in m.hh)}' for k in range(6)))
    print(f'預測 {m.predN} 次，正確 {m.predOk} 次（計分 {min(4, m.predOk)} VP，上限 4）' + (f'（{m.predOk * 100 // m.predN}%）' if m.predN else ''))
    if m.pvp: print(f'預言家預言得分：{m.pvp} VP')
    print('提示：若你常直接攻擊星級最高者，可能是「照星級行動」；星級只是估計。')


EN = {'hunter': 'Hunter', 'guard': 'Guardian', 'cap': 'Capitalist', 'manip': 'Manipulator', 'dbl': 'Double-agent', 'obs': 'Observer', 'honor': 'Honorable', 'avenge': 'Avenger', 'merch': 'Merchant', 'tough': 'Survivor', 'hermit': 'Hermit', 'gamble': 'Gambler'}
SEN = {'永遠採集': 'Always-collect', '永遠攻擊': 'Always-attack', '永遠背叛': 'Always-betray', '完全不攻擊': 'Never-attack', '追星級': 'Star-follower', '永遠防禦': 'Always-defend', '保守': 'Cautious', '激進': 'Aggressive', '操盤': 'Manipulative', '資本': 'Capital', '均衡': 'Balanced'}


EN.update(ROLE_EN)


def simulate(n, seed=None, quiet=False, table=None):
    """全 AI 模擬 n 局，回傳統計 dict"""
    if seed is not None: random.seed(seed)
    base = ['保守', '激進', '操盤', '資本', '均衡', '激進']
    D = dict(n=n, gw={k: 0 for k in GL}, gok={k: 0 for k in GL}, gn={k: 0 for k in GL},
             sw={}, sn={}, gaps=[], wvp=[], elim_r=[], fres=[], atk=0, hit=0, elim=0, vps={k: [] for k in GL}, sty={}, sg={})
    for k in range(n):
        g = Game(False, random.sample(table or base, 6)); rk = g.run()
        D['gaps'].append(g.vp(rk[0]) - g.vp(rk[1])); D['wvp'].append(g.vp(rk[0]))
        D['gw'][rk[0].goal] += 1; D['sw'][rk[0].sty] = D['sw'].get(rk[0].sty, 0) + 1
        for p in g.P:
            D.setdefault('galive', {}); D['galive'][p.goal] = D['galive'].get(p.goal, 0) + p.alive
            D['gn'][p.goal] += 1; D['gok'][p.goal] += g.goal_ok(p); D['sn'][p.sty] = D['sn'].get(p.sty, 0) + 1
            D['atk'] += p.atkN; D['hit'] += p.hits; D['fres'].append(p.res); D['vps'][p.goal].append(g.vp(p))
            t = D['sty'].setdefault(p.sty, dict(n=0, win=0, vp=0, alive=0, kills=0, res=0, ok=0, acts=[0] * 6))
            t['n'] += 1; t['win'] += p is rk[0]; t['vp'] += g.vp(p); t['alive'] += p.alive; t['kills'] += p.kills
            t['res'] += p.res; t['ok'] += g.goal_ok(p)
            for j in range(6): t['acts'][j] += sum(h[j] for h in p.hh)
            sg = D['sg'].setdefault((p.sty, p.goal), [0, 0, 0, 0, [0] * 6]); sg[0] += p is rk[0]; sg[1] += 1; sg[2] += g.goal_ok(p); sg[3] += g.vp(p)
            for j in range(6): sg[4][j] += sum(h[j] for h in p.hh)
            if not p.alive: D['elim'] += 1; D['elim_r'].append(p.out)
        if not quiet and (k + 1) % 1000 == 0: print(f'  已完成 {k + 1}/{n} 局', flush=True)
    return D


def report(D):
    n = D['n']
    print(f'\n模擬 {n} 局（全 AI，HUNT_HITS={HUNT_HITS}）')
    print(f'淘汰率 {D["elim"] / (6 * n):.1%}｜平均最終資源 {sum(D["fres"]) / len(D["fres"]):.1f}｜攻擊命中率 {D["hit"] / max(1, D["atk"]):.1%}｜第1-2名VP差 {sum(D["gaps"]) / n:.2f}｜冠軍平均VP {sum(D["wvp"]) / n:.1f}')
    print('目標      達成率   奪冠率(基準16.7%)')
    for k in GL: print(f'{GL[k][0]:<5} {D["gok"][k] / max(1, D["gn"][k]):>7.1%} {D["gw"][k] / max(1, D["gn"][k]):>8.1%}')
    print('\n各 AI 策略表現（每名玩家平均）')
    print('策略   勝率    平均VP  存活率  平均擊殺  最終資源  目標達成   行動佔比(' + '/'.join(AC) + ')')
    for k, t in sorted(D['sty'].items(), key=lambda x: -x[1]['win'] / x[1]['n']):
        tot = sum(t['acts']) or 1; m = t['n']
        print(f'{k:<4} {t["win"] / m:>6.1%} {t["vp"] / m:>7.1f} {t["alive"] / m:>6.1%} {t["kills"] / m:>8.2f} {t["res"] / m:>8.1f} {t["ok"] / m:>8.1%}   ' + '/'.join(f'{a / tot:.0%}' for a in t['acts']))


def strat_test(n=3000, seed=None):
    """每種單一策略 vs 5 種一般 AI（各 1 名），看它是否明顯優於基準 16.7%"""
    out = {}
    for S in STRATS:
        D = simulate(n, seed, quiet=True, table=[S, '保守', '激進', '操盤', '資本', '均衡'])
        t = D['sty'][S]; m = t['n']; oth = [v for k, v in D['sty'].items() if k != S]
        out[S] = dict(n=m, win=t['win'] / m, vp=t['vp'] / m, alive=t['alive'] / m, kills=t['kills'] / m, res=t['res'] / m,
                      opp=sum(o['win'] for o in oth) / sum(o['n'] for o in oth))
    return out


def strat_report(R):
    print('\n單一策略測試（該策略 1 人 vs 5 種一般 AI；基準勝率 16.7%）')
    print('策略        勝率   對手平均  平均VP  存活率  擊殺  最終資源  判定')
    for k, v in R.items():
        se = math.sqrt(v['win'] * (1 - v['win']) / v['n']); d = v['win'] - 1 / 6
        verdict = '⚠ 可能 dominant' if d > 2 * se and v['win'] > .22 else '弱勢' if d < -2 * se and v['win'] < .12 else '在合理範圍' if abs(d) <= 2 * se else ('偏強' if d > 0 else '偏弱')
        print(f'{k:<6} {v["win"]:>7.1%} {v["opp"]:>8.1%} {v["vp"]:>7.1f} {v["alive"]:>6.1%} {v["kills"]:>5.2f} {v["res"]:>8.1f}  {verdict}（±{2 * se:.1%}）')


ZH = False
_font_done = False
EXPLAIN = {
    'win_goal': ('各隱藏目標奪冠率', '各隱藏目標最後拿到第一名的比例（只算持有該目標的玩家）。虛線 16.7% 代表完全公平，越貼近虛線越平衡。'),
    'ok_goal': ('各目標達成率', '各隱藏目標最後有完成的比例。太低代表太難、太高代表太容易（能力型目標持有即達成，所以是 100%）。'),
    'win_style': ('各 AI 風格奪冠率', '每種 AI 性格「每名玩家」的平均奪冠率。偏離虛線太多，表示該風格太強或太弱。'),
    'wvp': ('冠軍 VP 分布', '每局第一名最終 VP 的分布，用來看遊戲分數大致落在哪個區間。'),
    'gap': ('第 1、2 名 VP 差', '第一名與第二名的 VP 差距。越靠近 0 代表比賽越膠著，0 代表同分（靠資源、信用決勝）。'),
    'elim': ('各回合淘汰人數', '平均每局在各回合被淘汰的人數。前兩回合應為 0，後期逐漸增加代表風險逐步升高。'),
    'sty_win': ('各策略勝率', '五種 AI 風格每名玩家的勝率。虛線 16.7% 是公平基準。'),
    'sty_vp': ('平均 VP', '各風格每局最終平均 VP，分數高但勝率低，代表容易被別人高分贏過。'),
    'sty_mix': ('存活／達成／擊殺', '存活率、目標達成率與每名玩家平均擊殺數（×100）。看風格是靠活著還是靠打人得分。'),
    'act_mix': ('行動佔比', '各風格把行動點花在哪些行動上，用來看該風格的真實個性。'),
    'sty_res': ('平均最終資源', '各風格結束時平均剩多少資源，資源越多則換到的 VP 越多。'),
    'heat': ('策略 × 隱藏目標勝率', '縱軸是 AI 風格、橫軸是隱藏目標，數字是勝率(%)，顏色越深越強。可用來找每個目標最適合的打法。'),
    'st_win': ('單一策略勝率', '1 名玩家固定只用一種策略，對上 5 種一般 AI。誤差條是 95% 信賴區間；明顯高於虛線代表可能有 dominant strategy。'),
    'st_mix': ('存活／VP／資源', '單一策略的存活率、平均 VP 與最終資源。看它是穩健型還是高風險型。'),
}


def setup_font():
    """找系統裡的中文字型；找不到就改用英文標籤"""
    global ZH, _font_done
    if _font_done: return
    _font_done = True
    import matplotlib
    from matplotlib import font_manager as fm
    cand = ['Microsoft JhengHei', 'Microsoft YaHei', 'PingFang TC', 'PingFang SC', 'Heiti TC', 'Noto Sans CJK TC', 'Noto Sans CJK SC',
            'Noto Sans TC', 'Source Han Sans TC', 'WenQuanYi Zen Hei', 'WenQuanYi Micro Hei', 'SimHei', 'Arial Unicode MS', 'AR PL UMing TW']
    names = {f.name for f in fm.fontManager.ttflist}
    hit = [c for c in cand if c in names]
    matplotlib.rcParams['axes.unicode_minus'] = False
    if hit: matplotlib.rcParams['font.sans-serif'] = hit + list(matplotlib.rcParams['font.sans-serif']); ZH = True
    else: print('（找不到中文字型，圖表改用英文標籤；圖表意義請看上方文字說明）')


T = lambda zh, en: zh if ZH else en
gname = lambda k: GL[k][0] if ZH else EN[k]
sname = lambda k: k if ZH else SEN[k]


def cap(a, key, y=-.22):
    """在子圖下方加上圖表意義說明（需中文字型）"""
    if not ZH: return
    t = EXPLAIN[key][1]
    a.text(.5, y, '\n'.join(t[i:i + 23] for i in range(0, len(t), 23)), transform=a.transAxes, ha='center', va='top', fontsize=8, color='#555')


def ttl(a, key, en, **kw):
    a.set_title(T(EXPLAIN[key][0], en), **kw)


def _fig(rows, cols, title, w, h, hs=.8):
    import matplotlib.pyplot as plt
    setup_font(); fig, ax = plt.subplots(rows, cols, figsize=(w, h)); fig.suptitle(title, fontsize=15)
    fig.subplots_adjust(left=.06, right=.97, top=.9, bottom=.1, hspace=hs, wspace=.27)
    return plt, fig, ax


def labels(a, v, dy, fmt='{:.1f}', size=9):
    for i, x in enumerate(v): a.text(i, x + dy, fmt.format(x), ha='center', fontsize=size)


def plot(D):
    n = D['n']; ks = list(GL)
    plt, fig, ax = _fig(2, 3, T(f'黑箱協議 — {n} 局全 AI 模擬：目標平衡', f'BLACKBOX PROTOCOL - {n} AI-only games'), 16, 11)
    lab = [gname(k) for k in ks]
    c = ['#d64b4b', '#2f9e5f', '#c9951a', '#4b5bd6', '#8a5bd6', '#2a9db0']
    c = (c * 3)[:len(ks)]
    a = ax[0][0]; v = [D['gw'][k] / max(1, D['gn'][k]) * 100 for k in ks]; a.bar(lab, v, color=c); a.axhline(100 / 6, ls='--', c='gray'); ttl(a, 'win_goal', 'Win rate by hidden goal'); a.set_ylabel('%'); labels(a, v, .3); cap(a, 'win_goal')
    a = ax[0][1]; v = [D['gok'][k] / max(1, D['gn'][k]) * 100 for k in ks]; a.bar(lab, v, color=c); ttl(a, 'ok_goal', 'Goal completion rate'); a.set_ylabel('%'); labels(a, v, .5); cap(a, 'ok_goal')
    a = ax[0][2]; ss = list(D['sw']); v = [D['sw'][k] / D['sn'][k] * 100 for k in ss]
    a.bar([sname(k) for k in ss], v, color='#4b5bd6'); a.axhline(100 / 6, ls='--', c='gray'); ttl(a, 'win_style', 'Win rate per player by AI style'); a.set_ylabel('%'); labels(a, v, .3); cap(a, 'win_style')
    a = ax[1][0]; lo, hi = math.floor(min(D['wvp'])), math.ceil(max(D['wvp']))
    a.hist(D['wvp'], bins=[lo + i * .5 for i in range((hi - lo + 1) * 2)], color='#2f9e5f'); ttl(a, 'wvp', 'Winner VP distribution'); a.set_xlabel('VP'); cap(a, 'wvp')
    a = ax[1][1]; a.hist(D['gaps'], bins=[i * .5 for i in range(int(math.ceil(max(D['gaps']) + 1) * 2))], color='#c9951a'); ttl(a, 'gap', 'VP gap: 1st - 2nd'); a.set_xlabel('VP'); cap(a, 'gap')
    a = ax[1][2]; er = [D['elim_r'].count(r) / n for r in range(1, ROUNDS + 1)]
    a.bar(range(1, ROUNDS + 1), er, color='#d64b4b'); ttl(a, 'elim', 'Eliminations per game by round'); a.set_xlabel(T('回合', 'Round')); cap(a, 'elim')
    for a in ax[0][:2]: a.tick_params(axis='x', labelrotation=40, labelsize=8)


def plot_strategy(D):
    ss = sorted(D['sty'], key=lambda k: -D['sty'][k]['win'] / D['sty'][k]['n'])
    plt, fig, ax = _fig(2, 3, T(f'AI 策略分析（每名玩家平均，{D["n"]} 局）', f'AI strategy analysis ({D["n"]} games)'), 16, 11)
    lab = [sname(k) for k in ss]; T_ = D['sty']; f = lambda key: [T_[k][key] / T_[k]['n'] for k in ss]
    col = ['#4b5bd6', '#d64b4b', '#2f9e5f', '#c9951a', '#8a5bd6']
    a = ax[0][0]; v = [x * 100 for x in f('win')]; a.bar(lab, v, color=col); a.axhline(100 / 6, ls='--', c='gray'); ttl(a, 'sty_win', 'Win rate by AI strategy'); a.set_ylabel('%'); labels(a, v, .3); cap(a, 'sty_win')
    a = ax[0][1]; v = f('vp'); a.bar(lab, v, color=col); ttl(a, 'sty_vp', 'Average VP'); a.set_ylim(min(v) - 2, max(v) + 1); labels(a, v, .1); cap(a, 'sty_vp')
    a = ax[0][2]; w = .27; xs = range(len(ss))
    a.bar([x - w for x in xs], [x * 100 for x in f('alive')], w, label=T('存活率 %', 'Survival %'), color='#2f9e5f')
    a.bar(list(xs), [x * 100 for x in f('ok')], w, label=T('目標達成率 %', 'Goal completion %'), color='#c9951a')
    a.bar([x + w for x in xs], [x * 100 for x in f('kills')], w, label=T('擊殺數 ×100', 'Kills x100'), color='#d64b4b')
    a.set_xticks(list(xs)); a.set_xticklabels(lab); a.set_ylim(0, 118); a.legend(fontsize=8, loc='upper center', ncol=3); ttl(a, 'sty_mix', 'Survival / goal / kills'); cap(a, 'sty_mix')
    a = ax[1][0]; bottom = [0] * len(ss)
    for j, nm in enumerate(AC if ZH else ['Collect', 'Explore', 'Observe', 'Trade', 'Defend', 'Attack']):
        v = [T_[k]['acts'][j] / (sum(T_[k]['acts']) or 1) * 100 for k in ss]
        a.bar(lab, v, bottom=bottom, label=nm); bottom = [b + x for b, x in zip(bottom, v)]
    a.legend(fontsize=8, ncol=3); ttl(a, 'act_mix', 'Action mix (%)'); a.set_ylim(0, 118); cap(a, 'act_mix')
    a = ax[1][1]; v = f('res'); a.bar(lab, v, color=col); ttl(a, 'sty_res', 'Average final resources'); labels(a, v, .05); cap(a, 'sty_res')
    a = ax[1][2]; ks = list(GL)
    M = [[D['sg'].get((k, g), [0, 1])[0] / max(1, D['sg'].get((k, g), [0, 1])[1]) * 100 for g in ks] for k in ss]
    im = a.imshow(M, cmap='YlGnBu'); a.set_xticks(range(len(ks))); a.set_xticklabels([gname(g) for g in ks], rotation=60, fontsize=7)
    a.set_yticks(range(len(ss))); a.set_yticklabels(lab); ttl(a, 'heat', 'Win rate %: strategy x goal'); cap(a, 'heat', -.5)
    for i in range(len(ss)):
        for j in range(len(ks)): a.text(j, i, f'{M[i][j]:.0f}', ha='center', va='center', fontsize=7)
    plt.colorbar(im, ax=a, fraction=.04)
    for a in (ax[0][0], ax[0][1], ax[1][0], ax[1][1]): a.tick_params(axis='x', labelrotation=15)


def plot_strat_test(R):
    plt, fig, ax = _fig(1, 2, T('單一策略測試（1 名玩家 vs 5 種一般 AI）', 'Single-strategy test (1 player vs 5 normal AIs)'), 13, 6.5, .4)
    fig.subplots_adjust(bottom=.28)
    ks = list(R); lab = [sname(k) for k in ks]
    v = [R[k]['win'] * 100 for k in ks]; e = [2 * math.sqrt(R[k]['win'] * (1 - R[k]['win']) / R[k]['n']) * 100 for k in ks]
    ax[0].bar(lab, v, yerr=e, color=['#2f9e5f', '#d64b4b', '#8a5bd6', '#2a9db0', '#c9951a', '#6b7280'], capsize=4); ax[0].axhline(100 / 6, ls='--', c='gray')
    ttl(ax[0], 'st_win', 'Win rate (error bar = 95%)'); ax[0].set_ylabel('%'); ax[0].tick_params(axis='x', labelrotation=15)
    for i, x in enumerate(v): ax[0].text(i, x + e[i] + .3, f'{x:.1f}', ha='center', fontsize=9)
    cap(ax[0], 'st_win', -.3)
    w = .27; xs = range(len(ks))
    ax[1].bar([x - w for x in xs], [R[k]['alive'] * 100 for k in ks], w, label=T('存活率 %', 'Survival %'), color='#2f9e5f')
    ax[1].bar(list(xs), [R[k]['vp'] for k in ks], w, label=T('平均 VP', 'Avg VP'), color='#4b5bd6')
    ax[1].bar([x + w for x in xs], [R[k]['res'] for k in ks], w, label=T('平均最終資源', 'Avg final resources'), color='#c9951a')
    ax[1].set_xticks(list(xs)); ax[1].set_xticklabels(lab, rotation=15); ax[1].legend(fontsize=8); ttl(ax[1], 'st_mix', 'Survival / VP / resources'); cap(ax[1], 'st_mix', -.3)


def goal_rows(D, g):
    """某隱藏目標下，各 AI 風格的表現（依勝率排序）"""
    rows = []
    for s_ in D['sty']:
        sg = D['sg'].get((s_, g))
        if sg and sg[1] > 0:
            tot = sum(sg[4]) or 1
            rows.append(dict(s=s_, win=sg[0] / sg[1], n=sg[1], ok=sg[2] / sg[1], vp=sg[3] / sg[1], mix=[x / tot for x in sg[4]]))
    return sorted(rows, key=lambda r: -r['win'])


def goal_advice(D, g):
    rows = goal_rows(D, g); b, c = rows[0], rows[1]
    se = math.sqrt((b['win'] * (1 - b['win']) / b['n']) + (c['win'] * (1 - c['win']) / c['n']))
    clear = b['win'] - c['win'] > 2 * se
    top = sorted(range(6), key=lambda i: -b['mix'][i])[:3]
    return rows, b, c, clear, '、'.join(f'{AC[i]}{b["mix"][i]:.0%}' for i in top)


CAT = {'hunter': '戰鬥型', 'avenge': '戰鬥型', 'gamble': '戰鬥型', 'tough': '戰鬥型', 'cap': '經濟型', 'merch': '經濟型', 'hermit': '經濟型',
       'manip': '操控型', 'dbl': '操控型', 'honor': '操控型', 'obs': '情報型', 'guard': '情報型'}
OK_RANGE = {'戰鬥型': (.45, .75), '經濟型': (.50, .80), '操控型': (.40, .70), '情報型': (.45, .75), '被動能力型': (1.0, 1.0)}
WIN_RANGE = (.14, .19)


def balance_check(D):
    """依設計分析的指標檢查：完成率、奪冠率、平均 VP、存活率（策略交叉勝率見最佳策略報告）"""
    print('\n平衡檢查（奪冠率理想區間 14–19%；完成率區間依目標類型）')
    print('目標      類型      完成率   區間      奪冠率   平均VP  存活率  判定')
    for k in GL:
        cat = '被動能力型' if k in ABILITY_GOALS else CAT[k]; lo, hi = OK_RANGE[cat]
        n_ = max(1, D['gn'][k]); ok = D['gok'][k] / n_; wr = D['gw'][k] / n_
        vp = sum(D['vps'][k]) / max(1, len(D['vps'][k])); al = D.get('galive', {}).get(k, 0) / n_
        tags = []
        if wr < WIN_RANGE[0]: tags.append('奪冠率偏低')
        if wr > WIN_RANGE[1]: tags.append('奪冠率偏高')
        if cat != '被動能力型' and ok < lo - 1e-9: tags.append('完成率偏低')
        if cat != '被動能力型' and ok > hi + 1e-9: tags.append('完成率偏高')
        print(f'{GL[k][0]:<5} {cat:<6} {ok:>7.1%} {lo:>4.0%}-{hi:<4.0%} {wr:>7.1%} {vp:>7.1f} {al:>6.1%}  ' + ('、'.join(tags) if tags else '✔ 在區間內'))


def best_goal_report(D):
    print('\n各隱藏目標的最佳策略建議（依「該目標 × AI 風格」的實際奪冠率統計）')
    for g in GL:
        rows, b, c, clear, mix = goal_advice(D, g)
        avg = sum(r['win'] * r['n'] for r in rows) / sum(r['n'] for r in rows)
        print(f'■ {GL[g][0]}：建議 {b["s"]}型（勝率 {b["win"]:.1%}，該目標平均 {avg:.1%}；達成率 {b["ok"]:.0%}；平均 VP {b["vp"]:.1f}）')
        print(f'    {"明顯優於其他風格" if clear else "與第二名（" + c["s"] + "型 " + format(c["win"], ".1%") + "）差距在誤差內，差不多"}｜主要行動：{mix}')


# ================= 各隱藏目標「最佳策略」報告：只輸出 PDF（可選 SVG），不輸出 PNG =================
# 版面：A4 橫式；圖表頁每頁 6 個目標（2 欄 × 3 列），水平長條圖；分析資訊另列成自動換行、自動調整列高的表格（可跨頁）。
REPORT = dict(                                                       # 字體、顏色、尺寸、間距全部集中在這裡
    page=(11.69, 8.27), dpi=100, bg='#FFFFFF', per_page=6,
    c_best='#D9A21B', c_bar='#8FA6C4', c_base='#7C828C', c_text='#222831', c_sub='#5F6673', c_grid='#E3E6EA',
    c_head='#E8EDF4', c_zebra='#F6F8FA', c_line='#C9CFD8',
    fs_head=17, fs_sub=10.5, fs_name=13.5, fs_rec=11, fs_tick=11, fs_value=10.5, fs_axis=10, fs_xtick=9.5, fs_base=9.5, fs_legend=10.5, fs_foot=9.5,
    fs_cell=10, fs_cellhead=10.5,
    margins=dict(left=.085, right=.97, top=.865, bottom=.115), hspace=.36, wspace=.22, title_ratio=(.34, 1.8),
    table=dict(l=.55, r=.55, t=.95, b=.6, pad=.07, line=1.4))


def _goal_info(D):
    """整理每個目標的分析資訊（數值全部來自 goal_advice / goal_rows，這裡不重新計算勝率）"""
    out = []
    for g in GL:
        rows, b, c, clear, mix = goal_advice(D, g)
        avg = sum(r['win'] * r['n'] for r in rows) / sum(r['n'] for r in rows)
        order = sorted(rows, key=lambda r: STYLE_ORDER.index(r['s']) if r['s'] in STYLE_ORDER else 99)
        out.append(dict(g=g, name=gname(g), best=b, second=c, clear=clear, mix=mix, avg=avg, order=order, ranked=rows))
    return out


def _verdict(x):
    return T('明顯優於其他風格', 'clearly better than the others') if x['clear'] else T('與第二名差距在誤差內', 'within noise of 2nd place')


def _mix_text(mix):
    top = sorted(range(6), key=lambda i: -mix[i])[:3]
    return '、'.join(f'{AC[i]}{mix[i]:.0%}' for i in top)


def _draw_panel(fig, spec, x, xmax, base):
    """單一目標：標題列（獨立 Axes）+ 水平長條圖（5 種策略由上到下，名稱放在左側，不擠在座標軸上）"""
    from matplotlib.gridspec import GridSpecFromSubplotSpec
    R = REPORT; sub = GridSpecFromSubplotSpec(2, 1, subplot_spec=spec, height_ratios=R['title_ratio'], hspace=.04)
    at = fig.add_subplot(sub[0]); at.axis('off'); a = fig.add_subplot(sub[1])
    b = x['best']
    at.text(0, .5, x['name'], ha='left', va='center', fontsize=R['fs_name'], fontweight='bold', color=R['c_text'], transform=at.transAxes)
    at.text(1, .5, T(f'建議策略：{b["s"]}型　勝率 {b["win"] * 100:.1f}%', f'Best: {sname(b["s"])}  {b["win"] * 100:.1f}%'), ha='right', va='center',
            fontsize=R['fs_rec'], color=R['c_sub'], transform=at.transAxes)
    names = [sname(r['s']) for r in x['order']]; v = [r['win'] * 100 for r in x['order']]; n = len(v)
    ypos = list(range(n))
    a.barh(ypos, v, height=.62, color=[R['c_best'] if r is b else R['c_bar'] for r in x['order']], zorder=3)
    a.plot([base, base], [-.45, n - .55], ls=(0, (5, 3)), lw=1.2, color=R['c_base'], zorder=2)
    a.text(base, -.95, T(f'基準線 {base:.1f}%', f'Baseline {base:.1f}%'), ha='center', va='center', fontsize=R['fs_base'], color=R['c_base'])   # 頂端留白列，不會碰到長條
    for yy, val, r in zip(ypos, v, x['order']):
        a.text(xmax * .985, yy, f'{val:.1f}', ha='right', va='center', fontsize=R['fs_value'], fontweight='bold' if r is b else 'normal', color=R['c_text'], zorder=5,
               bbox=dict(boxstyle='square,pad=0.1', fc=R['bg'], ec='none'))
    a.set_xlim(0, xmax); a.set_ylim(n - .35, -1.4)
    a.set_yticks(ypos); a.set_yticklabels(names, fontsize=R['fs_tick'], color=R['c_text'])
    for lab, r in zip(a.get_yticklabels(), x['order']):
        if r is b: lab.set_fontweight('bold')
    a.set_xticks(range(0, int(xmax) + 1, 10)); a.tick_params(axis='x', labelsize=R['fs_xtick'], colors=R['c_sub'], length=3); a.tick_params(axis='y', length=0)
    a.set_xlabel(T('勝率 (%)', 'Win rate (%)'), fontsize=R['fs_axis'], color=R['c_sub'], labelpad=3)
    a.xaxis.grid(True, color=R['c_grid'], lw=.8, zorder=0); a.set_axisbelow(True)
    for sp in ('top', 'right'): a.spines[sp].set_visible(False)
    for sp in ('left', 'bottom'): a.spines[sp].set_color('#B8BEC7')
    return a


def _chart_pages(D, info):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    R = REPORT; base = 100 / 6                                                    # 基準線沿用原本的 16.7%（1/6）
    xmax = float(math.ceil((max(r['win'] * 100 for x in info for r in x['order']) + 6) / 5.0) * 5)   # 所有頁共用同一個橫軸尺度
    per = R['per_page']; pages = [info[k:k + per] for k in range(0, len(info), per)]; figs = []
    for pg, chunk in enumerate(pages):
        fig = plt.figure(figsize=R['page'], dpi=R['dpi'], facecolor=R['bg'])
        gs = fig.add_gridspec(3, 2, hspace=R['hspace'], wspace=R['wspace'], **R['margins'])
        for k, x in enumerate(chunk): _draw_panel(fig, gs[k // 2, k % 2], x, xmax, base)
        fig.text(R['margins']['left'], .955, T(f'各隱藏目標的最佳策略分析（圖表 {pg + 1} / {len(pages)}）', f'Best strategy per hidden goal (charts {pg + 1} / {len(pages)})'), ha='left', va='center', fontsize=R['fs_head'], fontweight='bold', color=R['c_text'])
        fig.text(R['margins']['left'], .915, T(f'全 AI 模擬 {D["n"]} 局｜每張圖列出 5 種 AI 風格在該目標下的勝率｜橫軸尺度（0–{xmax:.0f}%）在所有頁面一致｜詳細分析見後面的表格', f'{D["n"]} all-AI games | 5 AI styles per goal | same x-scale on all pages | see tables for details'),
                 ha='left', va='center', fontsize=R['fs_sub'], color=R['c_sub'])
        h = [Patch(facecolor=R['c_best'], label=T('最佳策略（該目標下勝率最高的 AI 風格）', 'Best style for the goal')), Patch(facecolor=R['c_bar'], label=T('其他策略', 'Other styles')),
             Line2D([0], [0], color=R['c_base'], ls=(0, (5, 3)), lw=1.4, label=T(f'基準線 {base:.1f}%（六人遊戲的隨機期望勝率 1/6）', f'Baseline {base:.1f}% (random expectation 1/6)'))]
        fig.legend(handles=h, loc='lower center', ncol=3, frameon=False, fontsize=R['fs_legend'], bbox_to_anchor=(.5, .012))
        figs.append(fig)
    return figs


# ---------- 表格：自動換行 + 依文字量自動調整列高 + 可跨頁 ----------
def _tokens(s):
    toks = re.findall(r'[A-Za-z0-9.%:+\-/]+|\s+|.', s); out = []
    for t in toks:
        if out and t in '、，。；：）」』': out[-1] += t          # 標點不得出現在行首
        else: out.append(t)
    return out


def _wrap(s, width, meas):
    lines = []; cur = ''
    for tok in _tokens(s):
        if tok.isspace() and not cur: continue
        if not cur or meas(cur + tok) <= width:
            cur += tok
            while meas(cur) > width and len(cur) > 1:                  # 單一詞比欄寬還長 → 逐字切
                k = len(cur)
                while k > 1 and meas(cur[:k]) > width: k -= 1
                lines.append(cur[:k]); cur = cur[k:]
        else: lines.append(cur.rstrip()); cur = tok.lstrip()
    if cur: lines.append(cur)
    return lines or ['']


def _table_pages(title, sub, cols, rows, mark_rows=None, group=None):
    """cols: [(表頭, 欄寬(吋), 對齊)]；rows: [[文字...]]；回傳多張 Figure（表頭在每頁重複）"""
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    from matplotlib.patches import Rectangle
    R = REPORT; TB = R['table']; W, H = R['page']; pad = TB['pad']; dpi = R['dpi']
    probe = plt.figure(figsize=R['page'], dpi=dpi); rend = probe.canvas.get_renderer()
    fp = FontProperties(size=R['fs_cell']); fph = FontProperties(size=R['fs_cellhead'], weight='bold'); cache = {}
    def meas_c(t):
        k = ('c', t)
        if k not in cache: cache[k] = rend.get_text_width_height_descent(t, fp, False)[0] / dpi
        return cache[k]
    def meas_h(t): return rend.get_text_width_height_descent(t, fph, False)[0] / dpi
    scale = (W - TB['l'] - TB['r']) / sum(c[1] for c in cols); cols = [(h, w * scale, al) for h, w, al in cols]       # 欄寬依頁寬等比例調整
    lh = R['fs_cell'] * TB['line'] / 72; lhh = R['fs_cellhead'] * TB['line'] / 72
    hlines = [_wrap(h, w - 2 * pad, meas_h) for h, w, _ in cols]; hh = max(len(l) for l in hlines) * lhh + 2 * pad
    prep = []
    for r in rows:
        cells = [_wrap(str(t), w - 2 * pad, meas_c) for t, (h, w, _) in zip(r, cols)]
        prep.append((cells, max(len(c) for c in cells) * lh + 2 * pad))
    body_top = TB['t'] + hh; body_h = H - TB['b'] - body_top
    chunks, cur, used = [], [], 0.0
    gh = {}
    if group:
        for idx, (cells, h) in enumerate(prep): gh[group(idx)] = gh.get(group(idx), 0) + h          # 同一個目標的列盡量不拆到兩頁
    for idx, (cells, h) in enumerate(prep):
        new_group = group and (idx == 0 or group(idx) != group(idx - 1))
        need = gh[group(idx)] if new_group and gh[group(idx)] <= body_h else h
        if cur and used + need > body_h: chunks.append(cur); cur, used = [], 0.0
        cur.append(idx); used += h
    if cur: chunks.append(cur)
    plt.close(probe); figs = []
    for pn, chunk in enumerate(chunks):
        fig = plt.figure(figsize=R['page'], dpi=dpi, facecolor=R['bg']); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis('off')
        fig._cells = []
        ax.text(TB['l'], .42, title + (T(f'（{pn + 1} / {len(chunks)}）', f' ({pn + 1} / {len(chunks)})') if len(chunks) > 1 else ''), ha='left', va='center', fontsize=R['fs_head'], fontweight='bold', color=R['c_text'])
        ax.text(TB['l'], .75, sub, ha='left', va='center', fontsize=R['fs_sub'], color=R['c_sub'])
        y = TB['t']; x0s = [TB['l'] + sum(c[1] for c in cols[:i]) for i in range(len(cols))]
        for ci, ((h, w, al), lines) in enumerate(zip(cols, hlines)):                                  # 表頭
            ax.add_patch(Rectangle((x0s[ci], y), w, hh, fc=R['c_head'], ec=R['c_line'], lw=.7))
            for li, ln in enumerate(lines):
                tx = x0s[ci] + (w / 2 if al == 'center' else pad)
                t = ax.text(tx, y + pad + li * lhh, ln, ha='center' if al == 'center' else 'left', va='top', fontsize=R['fs_cellhead'], fontweight='bold', color=R['c_text']); fig._cells.append(((x0s[ci], y, x0s[ci] + w, y + hh), t))
        y += hh
        for rn, idx in enumerate(chunk):
            cells, h = prep[idx]
            for ci, ((_, w, al), lines) in enumerate(zip(cols, cells)):
                strong = mark_rows and mark_rows(idx)
                ax.add_patch(Rectangle((x0s[ci], y), w, h, fc=('#FBF3DC' if strong else (R['c_zebra'] if rn % 2 else R['bg'])), ec=R['c_line'], lw=.7))
                for li, ln in enumerate(lines):
                    tx = x0s[ci] + (w / 2 if al == 'center' else pad)
                    t = ax.text(tx, y + pad + li * lh, ln, ha='center' if al == 'center' else 'left', va='top', fontsize=R['fs_cell'], color=R['c_text']); fig._cells.append(((x0s[ci], y, x0s[ci] + w, y + h), t))
            y += h
        figs.append(fig)
    return figs


def _summary_tables(info):
    cols = [(T('隱藏目標', 'Goal'), .95, 'left'), (T('建議策略', 'Best style'), .85, 'center'), (T('勝率 (%)', 'Win %'), .7, 'center'), (T('該目標平均 %', 'Goal avg %'), 1.0, 'center'),
            (T('第二名', '2nd place'), 1.3, 'center'), (T('判定', 'Verdict'), 1.9, 'left'), (T('達成率', 'Completion'), .7, 'center'), (T('平均 VP', 'Avg VP'), .7, 'center'), (T('主要行動（前三）', 'Top actions'), 2.2, 'left')]
    rows = [[x['name'], T(f'{x["best"]["s"]}型', sname(x['best']['s'])), f'{x["best"]["win"] * 100:.1f}', f'{x["avg"] * 100:.1f}', T(f'{x["second"]["s"]}型　{x["second"]["win"] * 100:.1f}', f'{sname(x["second"]["s"])}  {x["second"]["win"] * 100:.1f}'),
             _verdict(x), f'{x["best"]["ok"]:.0%}', f'{x["best"]["vp"]:.1f}', _mix_text(x['best']['mix'])] for x in info]
    return _table_pages(T('18 個隱藏目標的策略分析總表', 'Strategy summary for all 18 hidden goals'), T('每個目標一列：最佳策略、與第二名比較、達成率、平均 VP 與該策略最常用的行動；勝率為持有該目標的玩家奪冠率；「第二名」欄為「策略　勝率 %」', 'One row per goal'), cols, rows)


def _detail_tables(info):
    cols = [(T('隱藏目標', 'Goal'), .95, 'left'), (T('策略', 'Style'), .8, 'center'), (T('名次', 'Rank'), .55, 'center'), (T('勝率 (%)', 'Win %'), .8, 'center'), (T('達成率', 'Completion'), .8, 'center'),
            (T('平均 VP', 'Avg VP'), .75, 'center'), (T('樣本數', 'N'), .75, 'center'), (T('主要行動（前三）', 'Top actions'), 3.2, 'left'), (T('備註', 'Note'), 1.6, 'left')]
    rows = []; best_rows = set()
    for x in info:
        for rk, r in enumerate(x['ranked'], 1):
            note = T('★ 建議策略（最佳）', '* best') if r is x['best'] else (T('第二名', '2nd') if r is x['second'] else '')
            if r is x['best']: best_rows.add(len(rows))
            rows.append([x['name'], sname(r['s']) if not ZH else r['s'], str(rk), f'{r["win"] * 100:.1f}', f'{r["ok"]:.0%}', f'{r["vp"]:.1f}', str(r['n']), _mix_text(r['mix']), note])
    return _table_pages(T('各隱藏目標 × 五種策略：完整資料', 'Detail: 18 goals x 5 styles'), T('每個目標列出 5 種 AI 風格（依勝率排序）；金色底為該目標的建議策略；主要行動是該風格實際花最多行動點的前三項', 'Sorted by win rate'), cols, rows, mark_rows=lambda i: i in best_rows, group=lambda i: i // 5)


def audit_figure(fig):
    """用文字邊界框檢查：文字互相重疊、超出頁面、長條遮住數值、表格文字超出儲存格"""
    from matplotlib.text import Text
    fig.canvas.draw(); rend = fig.canvas.get_renderer(); Wp, Hp = fig.bbox.width, fig.bbox.height; issues = []
    items = []
    for t in fig.findobj(Text):
        if not t.get_visible() or not t.get_text().strip(): continue
        try: bb = t.get_window_extent(rend)
        except Exception: continue
        if bb.width <= 0: continue
        items.append((t, bb))
    for t, bb in items:
        if bb.x0 < -1 or bb.y0 < -1 or bb.x1 > Wp + 1 or bb.y1 > Hp + 1: issues.append(('超出頁面', t.get_text()[:20]))
    for i in range(len(items)):
        bi = items[i][1]
        for j in range(i + 1, len(items)):
            bj = items[j][1]
            ox = min(bi.x1, bj.x1) - max(bi.x0, bj.x0); oy = min(bi.y1, bj.y1) - max(bi.y0, bj.y0)
            if ox > 1.5 and oy > 1.5: issues.append(('文字重疊', items[i][0].get_text()[:14], items[j][0].get_text()[:14]))
    from matplotlib.patches import Rectangle
    for ax in fig.axes:
        bars = [p.get_window_extent(rend) for p in ax.patches if isinstance(p, Rectangle) and p.get_zorder() == 3]
        for t in ax.texts:
            if not t.get_text().strip(): continue
            tb = t.get_window_extent(rend)
            for b in bars:
                if min(tb.x1, b.x1) - max(tb.x0, b.x0) > 1 and min(tb.y1, b.y1) - max(tb.y0, b.y0) > 1: issues.append(('數值壓到長條', t.get_text()[:14]))
    for rect, t in getattr(fig, '_cells', []):
        ax = fig.axes[0]; p0 = ax.transData.transform((rect[0], rect[1])); p1 = ax.transData.transform((rect[2], rect[3])); bb = t.get_window_extent(rend)
        if bb.x0 < min(p0[0], p1[0]) - 1 or bb.x1 > max(p0[0], p1[0]) + 1 or bb.y0 < min(p0[1], p1[1]) - 1 or bb.y1 > max(p0[1], p1[1]) + 1: issues.append(('文字超出儲存格', t.get_text()[:14]))
    return issues


def export_goal_report(D, outdir='blackbox_report', svg=False):
    """輸出完整報告 PDF（圖表 3 頁 + 總表 + 完整資料表）；svg=True 時另存每頁 SVG；不輸出任何 PNG。回傳 (檔案清單, 問題清單)"""
    import os
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    setup_font(); plt.rcParams['pdf.fonttype'] = 42; plt.rcParams['ps.fonttype'] = 42; plt.rcParams['svg.fonttype'] = 'path'; plt.rcParams['axes.unicode_minus'] = False
    os.makedirs(outdir, exist_ok=True); info = _goal_info(D)
    figs = _chart_pages(D, info) + _summary_tables(info) + _detail_tables(info); N = len(figs)
    for k, fig in enumerate(figs, 1): fig.text(.97, .014, T(f'第 {k} / {N} 頁', f'Page {k} / {N}'), ha='right', va='bottom', fontsize=REPORT['fs_foot'], color=REPORT['c_sub'])
    issues = []
    for k, fig in enumerate(figs, 1):
        for it in audit_figure(fig): issues.append((k,) + it)
    pdf = os.path.join(outdir, 'strategy_report.pdf'); paths = [pdf]
    with PdfPages(pdf, metadata={'Title': 'BLACKBOX PROTOCOL strategy report', 'Subject': 'hidden goal x AI style win rates'}) as pp:
        for fig in figs: pp.savefig(fig, facecolor=REPORT['bg'])
    if svg:
        os.makedirs(os.path.join(outdir, 'svg'), exist_ok=True)
        for k, fig in enumerate(figs, 1):
            f = os.path.join(outdir, 'svg', f'page_{k:02d}.svg'); fig.savefig(f, format='svg', facecolor=REPORT['bg']); paths.append(f)
    for fig in figs: plt.close(fig)
    return paths, issues


def explain():
    print('\n圖表說明')
    for k, (t, d) in EXPLAIN.items(): print(f'・{t}：{d}')
    print('・各隱藏目標的最佳策略：每個目標（子圖）比較五種 AI 風格的勝率，金色最高者即建議打法，並附上該風格的主要行動。')


def sim(n, seed=None, do_plot=True, strat=True, export=True, svg=False):
    import os
    print(f'執行檔案：{os.path.abspath(__file__)}')
    print(f'版本確認：賭徒 {GOAL_VP.get("gamble")} VP（備戰 {GAMB_SPENT}、命中 {GAMB_HITS}）｜觀察者 {GOAL_VP.get("obs")} VP、情報權重 {INFO_VP_OBS}｜攻擊成功回收 {ATK_GAIN}｜攻擊失敗扣 AP {ATK_FAIL_PEN}')
    D = simulate(n, seed); report(D)
    R = None
    if strat: R = strat_test(max(2000, n // 3), seed); strat_report(R)
    best_goal_report(D); explain()
    if export:                                                                   # 報告 PDF（不需要圖形視窗，也不輸出 PNG）
        paths, issues = export_goal_report(D, svg=svg)
        print('\n已輸出報告：'); [print('  ' + x) for x in paths]
        print(f'版面自動檢查：{"通過（無文字重疊、無超出頁面／儲存格）" if not issues else str(len(issues)) + " 個問題"}')
        for it in issues[:20]: print('   ', it)
    if do_plot:
        plot(D); plot_strategy(D)
        if R: plot_strat_test(R)
        import matplotlib.pyplot as plt; plt.show()      # 直接跳出圖表視窗


if __name__ == '__main__':
    a = sys.argv[1:]
    if '--play' in a: play()                      # 手動遊玩（互動）
    else:                                         # 預設：全自動模擬，不需任何選擇
        seed = int(a[a.index('--seed') + 1]) if '--seed' in a else None
        nums = [x for x in a if x.isdigit() and x != str(seed)]
        sim(int(nums[0]) if nums else 1000, seed=seed, do_plot='--noplot' not in a, strat='--nostrat' not in a, export='--noexport' not in a, svg='--svg' in a)
