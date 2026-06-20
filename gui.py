"""今日头条AI内容生成Agent V8.2 - 桌面GUI版。"""

import csv
import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = os.path.dirname(os.path.abspath(sys.executable))
else:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TextRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, s):
        if s:
            self.text_widget.after(0, self._append, s)

    def _append(self, s):
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, s)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")

    def flush(self):
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("今日头条AI内容生成Agent V8.2")
        self.geometry("780x640")
        self.resizable(True, True)
        self.configure(bg="#f5f5f5")
        self._running = False
        self._build_ui()
        sys.stdout = TextRedirector(self._log_text)
        sys.stderr = TextRedirector(self._log_text)

    def _build_ui(self):
        header = tk.Frame(self, bg="#1a73e8", height=48)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="今日头条AI内容生成Agent V8.2",
                 font=("微软雅黑", 14, "bold"), fg="white", bg="#1a73e8").pack(side=tk.LEFT, padx=16, pady=8)

        ops = tk.LabelFrame(self, text="操作", font=("微软雅黑", 10), bg="#f5f5f5", padx=12, pady=10)
        ops.pack(fill=tk.X, padx=12, pady=(12, 6))

        row1 = tk.Frame(ops, bg="#f5f5f5")
        row1.pack(fill=tk.X, pady=4)
        tk.Button(row1, text="📥 导入头条数据", font=("微软雅黑", 10), command=self._do_import, width=14).pack(side=tk.LEFT)
        tk.Button(row1, text="🏷️ 规则分类", font=("微软雅黑", 10), command=self._do_classify_rule, width=12, bg="#e8f0fe").pack(side=tk.LEFT, padx=6)
        tk.Button(row1, text="🤖 AI分类", font=("微软雅黑", 10), command=self._do_classify_ai, width=10).pack(side=tk.LEFT)
        tk.Label(row1, text="推荐先用规则分类（免费）", font=("微软雅黑", 9), bg="#f5f5f5", fg="#666").pack(side=tk.LEFT, padx=8)

        row2 = tk.Frame(ops, bg="#f5f5f5")
        row2.pack(fill=tk.X, pady=4)
        tk.Button(row2, text="✍️ 生成文章", font=("微软雅黑", 10), command=self._do_generate, width=14, bg="#e6f4ea").pack(side=tk.LEFT)
        tk.Label(row2, text="数量:", font=("微软雅黑", 9), bg="#f5f5f5").pack(side=tk.LEFT, padx=(16, 4))
        self._num_var = tk.StringVar(value="3")
        tk.Spinbox(row2, from_=1, to=20, textvariable=self._num_var, width=4, font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self._safe_var = tk.BooleanVar(value=True)
        tk.Checkbutton(row2, text="安全模式", variable=self._safe_var, font=("微软雅黑", 9), bg="#f5f5f5").pack(side=tk.LEFT, padx=12)

        row3 = tk.Frame(ops, bg="#f5f5f5")
        row3.pack(fill=tk.X, pady=(4, 0))
        tk.Button(row3, text="👁️ 预览", font=("微软雅黑", 10), command=self._do_dryrun, width=10).pack(side=tk.LEFT)
        tk.Button(row3, text="📊 Reward排名", font=("微软雅黑", 10), command=self._show_reward, width=12).pack(side=tk.LEFT, padx=6)
        tk.Button(row3, text="📈 数据概况", font=("微软雅黑", 10), command=self._show_stats, width=10).pack(side=tk.LEFT, padx=6)
        tk.Button(row3, text="📁 输出目录", font=("微软雅黑", 10), command=self._open_output, width=10).pack(side=tk.LEFT, padx=6)

        log_frame = tk.LabelFrame(self, text="运行日志", font=("微软雅黑", 10), bg="#f5f5f5", padx=8, pady=6)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 6))
        self._log_text = tk.Text(log_frame, height=14, font=("Consolas", 9), state="disabled", wrap=tk.WORD, bg="#1e1e1e", fg="#d4d4d4")
        scrollbar = ttk.Scrollbar(log_frame, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._log_text.pack(fill=tk.BOTH, expand=True)

        status_bar = tk.Frame(self, bg="#e0e0e0", height=28)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)
        self._status_var = tk.StringVar(value="就绪")
        tk.Label(status_bar, textvariable=self._status_var, font=("微软雅黑", 9), bg="#e0e0e0", fg="#333").pack(side=tk.LEFT, padx=12)

    def _set_running(self, running):
        self._running = running
        self._status_var.set("运行中..." if running else "就绪")

    def _run_in_thread(self, target, *args):
        if self._running:
            return
        self._set_running(True)
        def wrapper():
            try:
                target(*args)
            except Exception as e:
                print(f"\n❌ 错误: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.after(0, self._set_running, False)
        threading.Thread(target=wrapper, daemon=True).start()

    # ── 导入 ──
    def _do_import(self):
        path = filedialog.askopenfilename(title="选择头条导出的 xlsx", filetypes=[("Excel", "*.xlsx"), ("所有", "*.*")])
        if path:
            self._run_in_thread(self._run_import, path)

    def _run_import(self, path):
        from modules.import_xlsx import read_xlsx, merge_timeseries, update_articles_snapshot
        print(f"\n导入: {os.path.basename(path)}")
        records = read_xlsx(path)
        if not records:
            print("❌ 无有效数据")
            return
        os.makedirs(os.path.join(PROJECT_ROOT, "data"), exist_ok=True)
        ts = os.path.join(PROJECT_ROOT, "data", "timeseries.csv")
        ar = os.path.join(PROJECT_ROOT, "data", "articles.csv")
        a1, u1 = merge_timeseries(records, ts)
        a2, u2 = update_articles_snapshot(records, ar)
        print(f"\n✅ 导入完成! timeseries:+{a1} articles:+{a2}")

    # ── 规则分类 ──
    def _do_classify_rule(self):
        self._run_in_thread(self._run_classify_rule)

    def _run_classify_rule(self):
        from modules.rule_classifier import classify_and_update_csv
        csv_path = os.path.join(PROJECT_ROOT, "data", "articles.csv")
        if not os.path.isfile(csv_path):
            print("❌ 无数据，请先导入")
            return
        classify_and_update_csv(csv_path)
        print("\n✅ 规则分类完成")

    # ── AI分类 ──
    def _do_classify_ai(self):
        self._run_in_thread(self._run_classify_ai)

    def _run_classify_ai(self):
        from modules.data_pipeline import load_csv
        from modules.ai_client import call_ai_safe

        csv_path = os.path.join(PROJECT_ROOT, "data", "articles.csv")
        articles = load_csv(csv_path)
        unclassified = [a for a in articles if a.get("content_type") in ("", "未分类")]
        if not unclassified:
            print("✅ 所有文章已分类")
            return

        categories = ["保安故事", "快递人生", "网约车洞察", "失业转型", "职场感悟", "货车司机", "生活哲思", "其他"]
        total = len(unclassified)
        classified = 0

        for i in range(0, total, 10):
            batch = unclassified[i:i+10]
            titles = "\n".join([f"{j+1}. {a['title']}" for j, a in enumerate(batch)])
            prompt = f"判断标题内容类型，可选：{', '.join(categories)}\n\n{titles}\n\n输出JSON数组：[{{\"1\":\"保安故事\"}}]"
            result = call_ai_safe(prompt, fallback="", max_tokens=1000, timeout=60)
            if not result:
                continue
            try:
                for item in json.loads(result):
                    for k, v in item.items():
                        idx = int(k) - 1
                        if 0 <= idx < len(batch):
                            batch[idx]["content_type"] = v
                            classified += 1
            except Exception:
                pass
            print(f"  批次 {i//10+1} 完成")

        with open(csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
            fieldnames = list(rows[0].keys()) if rows else []
        title_map = {a["title"]: a.get("content_type", "未分类") for a in articles}
        for row in rows:
            if row["title"] in title_map:
                row["content_type"] = title_map[row["title"]]
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        print(f"\n✅ AI分类完成，更新 {classified} 篇")

    # ── 生成 ──
    def _do_generate(self):
        self._run_in_thread(self._run_generate, int(self._num_var.get()), self._safe_var.get(), False)

    def _do_dryrun(self):
        self._run_in_thread(self._run_generate, int(self._num_var.get()), False, True)

    def _run_generate(self, num, safe_run, dry_run):
        from modules.data_pipeline import load_csv_with_timeseries
        from modules.feedback_sync import load_stats, update_stats, save_stats, get_strategy_ranking, check_title_similarity
        from modules.strategy_evolver import evolve_weights
        from modules.content_ranker import select_best_strategy
        from modules.writer import generate_article

        ar = os.path.join(PROJECT_ROOT, "data", "articles.csv")
        ts = os.path.join(PROJECT_ROOT, "data", "timeseries.csv")
        articles = load_csv_with_timeseries(ar, ts)
        if not articles:
            print("❌ 无数据")
            return

        unclassified = sum(1 for a in articles if a.get("content_type") in ("", "未分类"))
        if unclassified == len(articles):
            print("❌ 请先分类")
            return

        state_dir = os.path.join(PROJECT_ROOT, "data")
        stats = load_stats(state_dir)
        stats = update_stats(stats, articles)
        ranking = get_strategy_ranking(stats)

        print("\n📊 策略排名:")
        for r in ranking:
            print(f"  {r['strategy']}: rolling={r['rolling_avg']:.4f} n={r['count']}")

        if not dry_run:
            save_stats(stats, state_dir)
            evolve_weights({}, stats, output_dir=state_dir)

        existing_titles = [a.get("title", "") for a in articles]
        generated = []

        for i in range(num):
            strategy = select_best_strategy(ranking)
            if dry_run:
                print(f"\n[{i+1}/{num}] 预览 → {strategy}")
                continue

            print(f"\n[{i+1}/{num}] 生成中... ({strategy})")
            article = generate_article(strategy, articles, stats)
            if article:
                title = article.get("title", "")
                is_sim, sim, sim_t = check_title_similarity(title, existing_titles)
                if is_sim:
                    print(f"  ⚠️ 标题相似 ({sim:.0%}): {sim_t[:30]}")
                    if not safe_run:
                        break
                    continue
                generated.append(article)
                existing_titles.append(title)
                print(f"  ✅ {title[:50]}")
            elif not safe_run:
                break

        if dry_run:
            print("\n✅ 预览完成")
            return

        if generated:
            day_dir = os.path.join(PROJECT_ROOT, "output", datetime.now().strftime("%Y-%m-%d"))
            os.makedirs(day_dir, exist_ok=True)
            for idx, a in enumerate(generated):
                safe = a.get('title', 'untitled')[:20].replace('/', '_').replace('\\', '_')
                with open(os.path.join(day_dir, f"{idx+1}_{safe}.txt"), "w", encoding="utf-8") as f:
                    f.write(f"标题：{a.get('title','')}\n\n")
                    for alt in a.get('alt_titles', []):
                        f.write(f"备选：{alt}\n")
                    f.write(f"\n{'='*40}\n\n{a.get('body','')}")
            print(f"\n✅ 生成 {len(generated)} 篇 | 保存: {day_dir}")

    # ── 辅助 ──
    def _show_reward(self):
        self._run_in_thread(self._run_show_reward)

    def _run_show_reward(self):
        from modules.data_pipeline import load_csv_with_timeseries
        from modules.reward_calculator import compute_reward
        articles = load_csv_with_timeseries(
            os.path.join(PROJECT_ROOT, "data", "articles.csv"),
            os.path.join(PROJECT_ROOT, "data", "timeseries.csv"))
        if not articles:
            print("❌ 无数据")
            return
        print(f"\n📊 Reward 排名（{len(articles)} 篇）")
        print(f"{'Reward':>10} {'CTR':>7} {'展现':>8} {'阅读':>7} {'分类':<10} 标题")
        print("-" * 75)
        for a in sorted(articles, key=lambda x: compute_reward(x), reverse=True):
            r = compute_reward(a)
            imp = a.get("impressions", 0)
            reads = a.get("reads", 0)
            ctr = f"{reads/imp*100:.1f}%" if imp > 0 else "-"
            print(f"{r:>10.6f} {ctr:>7} {imp:>8} {reads:>7} {a.get('content_type','未分类')[:8]:<10} {a['title'][:30]}")

    def _open_output(self):
        d = os.path.join(PROJECT_ROOT, "output")
        os.makedirs(d, exist_ok=True)
        os.startfile(d)

    def _show_stats(self):
        csv_path = os.path.join(PROJECT_ROOT, "data", "articles.csv")
        if not os.path.isfile(csv_path):
            messagebox.showinfo("数据概况", "暂无数据")
            return
        with open(csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        cats = {}
        total_reads = total_imp = 0
        for r in rows:
            cats[r.get("content_type", "未分类")] = cats.get(r.get("content_type", "未分类"), 0) + 1
            total_reads += int(r.get("reads", 0) or 0)
            total_imp += int(r.get("impressions", 0) or 0)
        lines = [f"📊 数据概况", "", f"文章: {len(rows)}", f"展现: {total_imp:,}", f"阅读: {total_reads:,}",
                 f"CTR: {total_reads/total_imp*100:.1f}%" if total_imp else "CTR: -", "", "分类:"]
        for c, n in sorted(cats.items(), key=lambda x: -x[1]):
            lines.append(f"  {c}: {n}篇")
        messagebox.showinfo("数据概况", "\n".join(lines))


if __name__ == "__main__":
    App().mainloop()
