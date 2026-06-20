"""今日头条AI内容生成Agent V8.2 - CLI 入口。"""

import argparse
import csv
import os
import sys
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

DATA_DIR = os.path.join(ROOT_DIR, "data")
ARTICLES_CSV = os.path.join(DATA_DIR, "articles.csv")
TIMESERIES_CSV = os.path.join(DATA_DIR, "timeseries.csv")

VERSION = "V8.2"


def cmd_import(args):
    from modules.import_xlsx import read_xlsx, merge_timeseries, update_articles_snapshot

    xlsx_path = args.file
    if not os.path.isabs(xlsx_path):
        xlsx_path = os.path.join(ROOT_DIR, xlsx_path)

    if not os.path.isfile(xlsx_path):
        print(f"❌ 文件不存在: {xlsx_path}")
        return

    records = read_xlsx(xlsx_path)
    if not records:
        print("❌ 未解析到任何记录")
        return

    if args.dry_run:
        print(f"\n🔍 预览模式")
        for r in records[:5]:
            print(f"  - {r['title'][:40]} | 展现:{r.get('impressions',0)} | 阅读:{r.get('reads',0)}")
        if len(records) > 5:
            print(f"  ... 还有 {len(records)-5} 条")
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    added_ts, updated_ts = merge_timeseries(records, TIMESERIES_CSV)
    added_ar, updated_ar = update_articles_snapshot(records, ARTICLES_CSV)

    print(f"\n✅ 导入完成！")
    print(f"  timeseries: 新增 {added_ts}, 更新 {updated_ts}")
    print(f"  articles: 新增 {added_ar}, 更新 {updated_ar}")
    print(f"\n💡 下一步：python main.py classify --rule-only")


def cmd_classify(args):
    if args.rule_only:
        from modules.rule_classifier import classify_and_update_csv
        classify_and_update_csv(ARTICLES_CSV, dry_run=args.dry_run)
        return

    if args.ai_only:
        _classify_ai_only(args.dry_run)
        return

    from modules.rule_classifier import classify_and_update_csv

    print("=" * 50)
    print("  分类模式：规则 + AI 混合")
    print("=" * 50)

    print("\n📌 第一步：规则分类")
    classify_and_update_csv(ARTICLES_CSV, dry_run=args.dry_run)

    if args.dry_run:
        return

    from modules.data_pipeline import load_csv
    articles = load_csv(ARTICLES_CSV)
    unclassified = [a for a in articles if a.get("content_type") in ("", "未分类")]

    if not unclassified:
        print(f"\n✅ 规则分类覆盖了所有文章")
        return

    print(f"\n📌 第二步：AI 补充分类（{len(unclassified)} 篇）")
    try:
        _classify_with_ai(unclassified, args.dry_run)
    except Exception as e:
        print(f"  ⚠️ AI 分类失败: {e}")


def _classify_ai_only(dry_run=False):
    from modules.data_pipeline import load_csv
    articles = load_csv(ARTICLES_CSV)
    if not articles:
        print("❌ 没有文章数据")
        return
    unclassified = [a for a in articles if a.get("content_type") in ("", "未分类")]
    if not unclassified:
        print("✅ 所有文章已分类")
        return
    print(f"📊 待分类: {len(unclassified)} 篇")
    _classify_with_ai(unclassified, dry_run)


def _classify_with_ai(articles, dry_run=False):
    from modules.ai_client import call_ai_safe

    categories = ["保安故事", "快递人生", "网约车洞察", "失业转型", "职场感悟", "货车司机", "生活哲思", "其他"]
    batch_size = 10
    classified = 0
    total = len(articles)

    for i in range(0, total, batch_size):
        batch = articles[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"  🔄 批次 {batch_num}/{total_batches}")
        titles = "\n".join([f"{j+1}. {a['title']}" for j, a in enumerate(batch)])
        prompt = f"""请根据以下标题判断内容类型。可选：{', '.join(categories)}

{titles}

严格输出 JSON 数组：[{{"1": "保安故事"}}, {{"2": "快递人生"}}]"""

        result = call_ai_safe(prompt, fallback="", max_tokens=1000, timeout=60)
        if not result:
            continue

        try:
            parsed = json.loads(result)
            for item in parsed:
                for idx_str, ct in item.items():
                    idx = int(idx_str) - 1
                    if 0 <= idx < len(batch):
                        batch[idx]["content_type"] = ct
                        classified += 1
        except Exception:
            pass

    if not dry_run:
        import csv as csv_mod
        with open(ARTICLES_CSV, "r", encoding="utf-8") as f:
            reader = csv_mod.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        title_to_type = {a["title"]: a.get("content_type", "未分类") for a in articles}
        for row in rows:
            if row["title"] in title_to_type:
                row["content_type"] = title_to_type[row["title"]]
        with open(ARTICLES_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv_mod.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    print(f"\n✅ AI 分类完成，更新 {classified} 篇")


def cmd_generate(args):
    from modules.data_pipeline import load_csv_with_timeseries
    from modules.feedback_sync import load_stats, update_stats, save_stats, get_strategy_ranking, check_title_similarity
    from modules.content_ranker import select_best_strategy
    from modules.strategy_evolver import evolve_weights
    from modules.writer import generate_article

    articles = load_csv_with_timeseries(ARTICLES_CSV, TIMESERIES_CSV)
    if not articles:
        print("❌ 没有文章数据，请先导入")
        return

    unclassified = sum(1 for a in articles if a.get("content_type") in ("", "未分类"))
    if unclassified == len(articles):
        print("❌ 所有文章都是'未分类'，请先运行: python main.py classify")
        return
    elif unclassified > 0:
        print(f"⚠️  还有 {unclassified}/{len(articles)} 篇未分类")

    stats = load_stats(DATA_DIR)
    stats = update_stats(stats, articles)
    save_stats(stats, DATA_DIR)

    if args.sync_data:
        print("✅ 数据同步完成")
        return

    ranking = get_strategy_ranking(stats)
    if not ranking:
        print("❌ 没有策略数据")
        return

    print(f"\n📊 策略排名：")
    for r in ranking:
        print(f"  {r['strategy']}: rolling={r['rolling_avg']:.4f} n={r['count']}")

    evolve_weights({}, stats, output_dir=DATA_DIR)

    existing_titles = [a.get("title", "") for a in articles]
    generated = []

    for i in range(args.num):
        strategy = select_best_strategy(ranking)

        if args.dry_run:
            print(f"\n[{i+1}/{args.num}] 预览 → 策略: {strategy}")
            continue

        print(f"\n[{i+1}/{args.num}] 生成中... (策略:{strategy})")
        article = generate_article(strategy, articles, stats)
        if article:
            title = article.get("title", "")
            is_similar, sim_score, sim_title = check_title_similarity(title, existing_titles)
            if is_similar:
                print(f"  ⚠️ 标题相似 ({sim_score:.0%}): {sim_title[:30]}...")
                if not args.safe_run:
                    break
                continue
            generated.append(article)
            existing_titles.append(title)
            print(f"  ✅ {title[:50]}")
        else:
            if not args.safe_run:
                print("  ❌ 生成失败")
                break

    if args.dry_run:
        print(f"\n✅ 预览完成")
        return

    if generated:
        _save_generated(generated)
        print(f"\n✅ 共生成 {len(generated)} 篇文章")


def _save_generated(articles):
    today = datetime.now().strftime("%Y-%m-%d")
    gen_dir = os.path.join(DATA_DIR, "generated")
    os.makedirs(gen_dir, exist_ok=True)

    for a in articles:
        title = a.get("title", "untitled")
        safe_name = "".join(c for c in title if c.isalnum() or c in " _-")[:50].strip()

        with open(os.path.join(gen_dir, f"{safe_name}.txt"), "w", encoding="utf-8") as f:
            f.write(f"标题: {title}\n")
            f.write(f"类型: {a.get('content_type', '')}\n")
            f.write(f"情感分: {a.get('emotion_score', '')}\n")
            f.write(f"传播分: {a.get('viral_score', '')}\n")
            f.write(f"{'='*50}\n\n")
            f.write(a.get("body", ""))

        json_path = os.path.join(gen_dir, f"{safe_name}.json")
        import json
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(a, f, ensure_ascii=False, indent=2)


def cmd_test(args):
    from modules.ai_client import test_connection
    ok = test_connection()
    print("✅ AI 连接正常" if ok else "❌ AI 连接失败")


def cmd_validate(args):
    from modules.data_pipeline import validate_csv_structure
    result = validate_csv_structure(ARTICLES_CSV)
    if result.get("valid"):
        print(f"✅ CSV 正常 | {result['row_count']} 行 | 字段: {result['fields']}")
        if result.get("needs_migration"):
            print(f"  ⚠️ 旧字段将自动迁移")
    else:
        print(f"❌ CSV 异常: {result.get('error', result.get('missing_fields', ''))}")


def cmd_reward(args):
    from modules.data_pipeline import load_csv_with_timeseries
    from modules.reward_calculator import compute_reward

    articles = load_csv_with_timeseries(ARTICLES_CSV, TIMESERIES_CSV)
    if not articles:
        print("❌ 无数据")
        return

    print(f"\n📊 Reward 排名（{len(articles)} 篇）\n")
    print(f"{'Reward':>10} {'CTR':>8} {'展现':>8} {'阅读':>7} {'分类':<10} 标题")
    print("-" * 80)

    for a in sorted(articles, key=lambda x: compute_reward(x), reverse=True):
        r = compute_reward(a)
        imp = a.get("impressions", 0)
        reads = a.get("reads", 0)
        ctr = reads / imp * 100 if imp > 0 else 0
        ct = a.get("content_type", "未分类")[:8]
        print(f"{r:>10.6f} {ctr:>7.1f}% {imp:>8} {reads:>7} {ct:<10} {a['title'][:30]}")


def main():
    parser = argparse.ArgumentParser(description=f"今日头条AI内容生成Agent {VERSION}")
    sub = parser.add_subparsers(dest="command")

    p_imp = sub.add_parser("import", help="导入头条 xlsx 数据")
    p_imp.add_argument("file", help="xlsx 文件路径")
    p_imp.add_argument("--dry-run", action="store_true")

    p_cls = sub.add_parser("classify", help="分类文章")
    p_cls.add_argument("--dry-run", action="store_true")
    p_cls.add_argument("--rule-only", action="store_true")
    p_cls.add_argument("--ai-only", action="store_true")

    p_gen = sub.add_parser("generate", help="生成文章")
    p_gen.add_argument("--num", type=int, default=1)
    p_gen.add_argument("--safe-run", action="store_true")
    p_gen.add_argument("--dry-run", action="store_true")
    p_gen.add_argument("--sync-data", action="store_true")

    sub.add_parser("test", help="测试 AI 连接")
    sub.add_parser("validate", help="校验 CSV 结构")
    sub.add_parser("reward", help="查看 reward 排名")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    {"import": cmd_import, "classify": cmd_classify, "generate": cmd_generate,
     "test": cmd_test, "validate": cmd_validate, "reward": cmd_reward}[args.command](args)


if __name__ == "__main__":
    main()
