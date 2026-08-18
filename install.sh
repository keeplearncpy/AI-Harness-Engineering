#!/bin/bash
# install.sh - 一键将 Harness 能力注入 CLI 工具
#
# 【本版修复】项目 agents 为嵌套目录结构：
#   agents/subagents/<agent_name>/<agent_name>.md + agent.yaml
#   agents/independent/<agent_name>/<agent_name>.md + agent.yaml
# 旧版 glob `agents/subagents/*.md` 匹配不到嵌套文件，改用 find 递归扫描；
# 且 OpenCode 配置不再硬依赖 opencode 命令在 PATH 中。

# 【关键修复】显式定义配置目录，避免 MINGW64 下 ~ 展开异常
OPENCODE_CONFIG="$HOME/.config/opencode"   # Windows 下即 C:\Users\18162\.config\opencode
CLAUDE_CONFIG="$HOME/.claude"

# ==========================================
# 1. 处理 --update / -u 参数
# ==========================================
if [ "$1" = "--update" ] || [ "$1" = "-u" ]; then
    echo "🔄 更新模式：清理旧链接并重新创建..."

    rm -f "$OPENCODE_CONFIG/agents/harness-"*
    rm -f "$OPENCODE_CONFIG/skills/harness-"*
    rm -f "$OPENCODE_CONFIG/command/harness-"*.md

    rm -f "$CLAUDE_CONFIG/agents/harness-"*
    rm -f "$CLAUDE_CONFIG/skills/harness-"*
    rm -f "$CLAUDE_CONFIG/commands/harness-"*.md

    echo "   → 旧链接清理完成"
    echo ""
fi

# 资源根目录
HARNESS_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

echo "🔧 AI Harness Engineering - CLI 工具配置向导"
echo "============================================"
echo "📂 资源根目录: $HARNESS_HOME"
echo "🎯 OpenCode 配置目录: $OPENCODE_CONFIG"
echo "🎯 Claude Code 配置目录: $CLAUDE_CONFIG"
echo ""

# ==========================================
# 辅助函数：创建链接或降级为复制
# ==========================================
safe_link() {
    local src="$1"
    local dest="$2"

    if [ ! -e "$src" ]; then
        echo "   ⚠️  源不存在，跳过: $(basename "$src")"
        return 1
    fi

    # 确保目标父目录存在
    mkdir -p "$(dirname "$dest")"

    # 尝试符号链接，失败则降级复制（Windows 无开发者模式时自动走复制）
    if ln -sfn "$src" "$dest" 2>/dev/null; then
        echo "   🔗 $(basename "$dest") -> symlink"
        return 0
    else
        rm -rf "$dest"
        cp -r "$src" "$dest"
        echo "   📋 $(basename "$dest") -> copied (symlink failed)"
        return $?
    fi
}

# ==========================================
# 【核心修复】递归扫描 agent 两大目录（兼容 嵌套/扁平 两种结构）
# 输出所有 agent 主体 .md 的完整路径，每行一个（路径含空格也安全）
# ==========================================
list_agent_md_files() {
    local dir
    for dir in \
        "$HARNESS_HOME/agents/subagents" \
        "$HARNESS_HOME/agents/independent"; do
        [ -d "$dir" ] || continue
        find "$dir" -type f -name "*.md" ! -name "README.md" 2>/dev/null
    done
    # agents 根目录下直接平铺的 .md（如有），兜底不遗漏
    [ -d "$HARNESS_HOME/agents" ] && \
        find "$HARNESS_HOME/agents" -maxdepth 1 -type f -name "*.md" ! -name "README.md" 2>/dev/null
    return 0
}

# ==========================================
# 把扫描到的 agents 安装到目标目录（$1 = 目标 agents 目录）
# 命名约定（文件名已带 harness- 前缀则不重复添加）：
#   <name>.md  -> harness-<name>.md          （OpenCode/Claude 识别加载）
#   harness-<name>.md -> harness-<name>.md   （原样保留）
#   agent.yaml -> harness-<name>.agent.yaml  （harness 元数据备份，CLI 会忽略，不需要可删）
# ==========================================
install_agents_to() {
    local dest_dir="$1"
    local seen=" "

    mkdir -p "$dest_dir"

    while IFS= read -r md_file; do
        [ -f "$md_file" ] || continue

        local agent_dir agent_name
        agent_dir="$(dirname "$md_file")"
        agent_name="$(basename "$md_file" .md)"

        # 同名 agent 已安装则跳过（subagents 优先）
        case "$seen" in *" $agent_name "*) continue ;; esac
        seen="$seen$agent_name "

        # 文件名已带 harness- 前缀时不重复添加
        install_name="$agent_name"
        case "$agent_name" in
            harness-*) install_name="$agent_name" ;;
            *)         install_name="harness-$agent_name" ;;
        esac

        # 1) agent 主体 .md
        safe_link "$md_file" "$dest_dir/$install_name.md"

        # 2) 同目录伴随的 agent.yaml 元数据
        if [ -f "$agent_dir/agent.yaml" ]; then
            safe_link "$agent_dir/agent.yaml" "$dest_dir/$install_name.agent.yaml"
        fi
    done < <(list_agent_md_files)
}

# ==========================================
# 2. Claude Code 配置
# ==========================================
if command -v claude &> /dev/null; then
    echo "✅ 检测到 Claude Code"
    mkdir -p "$CLAUDE_CONFIG/skills" "$CLAUDE_CONFIG/agents" "$CLAUDE_CONFIG/commands"

    safe_link "$HARNESS_HOME/skills/templates"  "$CLAUDE_CONFIG/skills/harness-templates"
    safe_link "$HARNESS_HOME/skills/schemas"    "$CLAUDE_CONFIG/skills/harness-schemas"
    safe_link "$HARNESS_HOME/skills/checklists" "$CLAUDE_CONFIG/skills/harness-checklists"

    # 【修复】递归安装嵌套目录下的 agents
    install_agents_to "$CLAUDE_CONFIG/agents"

    [ -f "$HARNESS_HOME/commands/harness-new.md" ] && \
        safe_link "$HARNESS_HOME/commands/harness-new.md" "$CLAUDE_CONFIG/commands/harness-new.md"
    [ -f "$HARNESS_HOME/commands/harness-iterate.md" ] && \
        safe_link "$HARNESS_HOME/commands/harness-iterate.md" "$CLAUDE_CONFIG/commands/harness-iterate.md"

    echo "   → Claude Code 配置完成"
else
    echo "⚠️  未检测到 claude 命令，跳过 Claude Code 配置"
fi
echo ""

# ==========================================
# 3. OpenCode 配置
# 【修复】配置文件不依赖 opencode 命令在 PATH 中：
#        即使 Git Bash 里检测不到 opencode，也照装到 $OPENCODE_CONFIG
# ==========================================
if command -v opencode &> /dev/null; then
    echo "✅ 检测到 OpenCode"
else
    echo "⚠️  未检测到 opencode 命令（可能不在 PATH），仍会写入配置: $OPENCODE_CONFIG"
fi

mkdir -p "$OPENCODE_CONFIG/agents" "$OPENCODE_CONFIG/skills" "$OPENCODE_CONFIG/command"

# Skills
safe_link "$HARNESS_HOME/skills/templates"  "$OPENCODE_CONFIG/skills/harness-templates"
safe_link "$HARNESS_HOME/skills/schemas"    "$OPENCODE_CONFIG/skills/harness-schemas"
safe_link "$HARNESS_HOME/skills/checklists" "$OPENCODE_CONFIG/skills/harness-checklists"

# Agents - 递归扫描 subagents / independent / agents 根目录
install_agents_to "$OPENCODE_CONFIG/agents"

# Commands（本地工作流入口：/harness-new、/harness-iterate）
for cmd_file in "$HARNESS_HOME"/commands/harness-*.md; do
    [ -f "$cmd_file" ] || continue
    safe_link "$cmd_file" "$OPENCODE_CONFIG/command/$(basename "$cmd_file")"
done

echo "   → OpenCode 配置完成"

# ==========================================
# 4. 安装验证
# ==========================================
echo ""
echo "🔍 安装验证:"
INSTALLED_COUNT=$(ls "$OPENCODE_CONFIG/agents/harness-"* "$OPENCODE_CONFIG/skills/harness-"* 2>/dev/null | wc -l)
if [ "$INSTALLED_COUNT" -gt 0 ]; then
    echo "   ✅ 成功安装 $INSTALLED_COUNT 个 Harness 组件到 $OPENCODE_CONFIG"
    ls -1 "$OPENCODE_CONFIG/agents/harness-"* "$OPENCODE_CONFIG/skills/harness-"* 2>/dev/null | sed 's/^/      /'
else
    echo "   ❌ 未安装任何组件！请检查资源目录结构:"
    echo "      find \"$HARNESS_HOME/agents\" -name \"*.md\""
fi

# ==========================================
# 5. 完成提示
# ==========================================
echo ""
echo "🎉 安装完成！进入任意项目目录，启动 CLI 即可使用。"
echo "   Claude Code: claude → /harness-new 项目名称"
echo "   OpenCode:    opencode → 对话中调用 harness-fsd_generator"
echo ""
echo "💡 提示：如果后续新增/删除了 Agent 文件，请运行 ./install.sh --update 刷新链接。"