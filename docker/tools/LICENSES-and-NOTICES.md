# 来源与许可记录

仓库快照信息见 `repositories/manifest.json`，按下载时 GitHub 默认分支和 commit 归档；源码快照不含 Git 历史。按每个仓库根目录中的 LICENSE/NOTICE 及该 manifest 的许可说明分别确认使用条件；`NOASSERTION` 表示此清单未确认 SPDX 许可，不等于授予许可。

- `BLHX`、`Pozhen-Agent`：未发现根目录许可声明，`NOASSERTION`。
- `Cruiser-Agent`：Apache-2.0。
- `jadx`：Apache-2.0，保留 LICENSE/NOTICE。
- `radare2`：以 LGPLv3 为主，包含依赖/插件等不同许可；阅读 COPYING.md、doc/licenses。
- `pwntools`：以 MIT 为主，部分内容是 GPL/BSD 等许可；阅读 LICENSE-pwntools.txt 与文件级声明。
- `angr`：BSD-2-Clause。
- `PayloadsAllTheThings`：MIT。

源码快照原样保留上游文件。修改或再分发前逐项检查对应仓库 LICENSE、NOTICE、第三方依赖许可与商标要求；没有许可声明的源码只作为本地阅读参考，公开再分发前应向维护者确认。

## Nikto 2.6.1

Upstream: https://github.com/sullo/nikto (tag 2.6.1). The source archive is redistributed unmodified and contains upstream `COPYING` and `COPYING.LibWhisker` files. Check those files for applicable license terms.


## 二进制和 Python 依赖

Ghidra、JADX、radare2 和 `requirements-linux.txt` 中 Python 包各有独立许可与依赖。官方发行包未修改；版本/官方下载链接见 `tools/releases/SOURCES.txt`，下载文件 SHA-256 见 `tools/releases/SOURCES.sha256`。构建或再分发前核对发行包随附许可及依赖许可。
