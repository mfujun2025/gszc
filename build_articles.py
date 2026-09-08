#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_articles.py —— 公司注册资讯站：文章构建辅助 + sitemap.xml 自动生成

【这是什么】
把原来需要手动运行的 build-sitemap.ps1（PowerShell）逻辑用 Python 实现了一遍，
输出格式、排序、lastmod 规则、域名前缀与原脚本完全一致。
以后每天定时任务新增文章后，只要在站点目录运行一次：

    python build_articles.py

脚本会自动扫描目录下全部文章页并重新生成 sitemap.xml，无需手工编辑，
新文章的完整 URL 会被自动收录。

【集成到你自己的发文逻辑】
如果你在本文件里写“生成新文章”的函数，只需在新文章 html 写完之后调用一行：

    from build_articles import build_sitemap
    build_sitemap()          # 默认重建本脚本所在目录的 sitemap.xml
    # 也可显式传目录：build_sitemap(r"C:\\path\\company-reg-site")

【兼容性】
- 仅使用 Python 标准库，Python 3.7+ 均可运行，无需 pip 安装任何依赖；
- Windows / Linux 均可运行；
- 以 UTF-8 无 BOM、CRLF 换行写出，与原 build-sitemap.ps1 产物保持一致。
"""

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

# ============ 站点配置（换域名时只改这里；中文域名必须用 Punycode，xn-- 开头）============
BASE_URL = "https://xn--55qwct6gv65b.xn--fiqs8s"

# 不收录进 sitemap 的页面
EXCLUDE_PAGES = {"article-template.html"}
# 固定页：单独排序，不按文章页规则处理
FIXED_PAGES = {"index.html", "latest.html", "about.html"}
# 文章文件名结尾的日期，用于自动取 lastmod
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})$")


def _url_block(loc: str, lastmod: str, changefreq: str, priority: str) -> str:
    """生成一条 <url> 记录（缩进/换行与原 ps1 脚本一致）。"""
    return (
        "  <url>\r\n"
        f"    <loc>{loc}</loc>\r\n"
        f"    <lastmod>{lastmod}</lastmod>\r\n"
        f"    <changefreq>{changefreq}</changefreq>\r\n"
        f"    <priority>{priority}</priority>\r\n"
        "  </url>\r\n"
    )


def build_sitemap(site_dir=None, base_url: str = BASE_URL, out_name: str = "sitemap.xml"):
    """
    扫描站点目录，重新生成 sitemap.xml。

    规则（与 build-sitemap.ps1 完全对齐）：
      1) 首页 / ：weekly，1.0，lastmod=今天
      2) latest.html ：daily，0.9，lastmod=今天
      3) 其余 *.html（排除模板页和固定页）按文件名排序，monthly，0.7；
         lastmod 取文件名结尾的 -yyyy-MM-dd，取不到则用今天
      4) about.html 固定排最后：monthly，0.5，lastmod=今天

    :param site_dir: 站点目录；None 时取本脚本所在目录
    :param base_url: 站点域名（Punycode）
    :param out_name: 输出文件名，默认 sitemap.xml
    :return: (输出文件 Path, 收录 URL 总数)
    """
    site_dir = Path(site_dir).resolve() if site_dir else Path(__file__).resolve().parent
    if not site_dir.is_dir():
        raise FileNotFoundError(f"站点目录不存在：{site_dir}")

    today = _dt.date.today().isoformat()
    blocks = []

    # ① 首页 + ② 最新资讯列表
    blocks.append(_url_block(f"{base_url}/", today, "weekly", "1.0"))
    blocks.append(_url_block(f"{base_url}/latest.html", today, "daily", "0.9"))

    # ③ 文章页：文件名按字母序，lastmod 自动取文件名日期
    #    baidu_verify_ 开头的是搜索引擎站点验证文件，须留在根目录但不进 sitemap
    articles = sorted(
        p for p in site_dir.glob("*.html")
        if p.name not in EXCLUDE_PAGES
        and p.name not in FIXED_PAGES
        and not p.name.startswith("baidu_verify_")
    )
    for page in articles:
        m = _DATE_RE.search(page.stem)
        lastmod = m.group(1) if m else today
        blocks.append(_url_block(f"{base_url}/{page.name}", lastmod, "monthly", "0.7"))

    # ④ 关于我们放最后
    blocks.append(_url_block(f"{base_url}/about.html", today, "monthly", "0.5"))

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\r\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\r\n'
        + "".join(blocks)
        + "</urlset>\r\n"
    )

    out_path = site_dir / out_name
    # 用 bytes 写出：保证 UTF-8 无 BOM、CRLF 不被平台改写
    out_path.write_bytes(xml.encode("utf-8"))
    return out_path, len(blocks), [p.name for p in articles]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="扫描站点文章页，自动重新生成 sitemap.xml（与 build-sitemap.ps1 等价）"
    )
    parser.add_argument("--dir", default=None,
                        help="站点目录，默认取本脚本所在目录")
    parser.add_argument("--base", default=BASE_URL,
                        help=f"站点域名（Punycode），默认 {BASE_URL}")
    args = parser.parse_args(argv)

    try:
        out_path, total, articles = build_sitemap(args.dir, args.base)
    except Exception as exc:  # noqa: BLE001 - 命令行入口统一兜底打印
        print(f"[错误] sitemap 生成失败：{exc}", file=sys.stderr)
        return 1

    print(f"已生成 sitemap：{out_path}")
    print(f"共收录 {total} 个 URL，其中文章页 {len(articles)} 篇：")
    for name in articles:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
