#!/bin/bash
# install.sh - 一键将 Harness 能力注入 CLI 工具

# 【关键修复】显式定义配置目录，避免 MINGW64 下 ~ 展开异常
OPENCODE_CONFIG="$HOME/.config/opencode"
CLAUDE_CONFIG="$HOME/.claude"

# ==========================================
# 1. 处理 --update / -u 参数
# ==========================================
if [ "$1" = "--update" ] || [ "$1" = "-u" ]; then
    echo "🔄 更新模式：清理旧链接并重新创建..."
    
    rm -f "$OPENCODE_CONFIG/agents/harness-"*
    rm -f "$OPENCODE_CONFIG/skills/harness-"*
    
    rm -f "$CLAUDE_CONFIG/agents/harness-"*
    rm -f "$CLAUDE_CONFIG/skills/harness-"*
    rm -f "$CLAUDE_CONFIG/commands/harness-"*.md
    
    echo "   → 旧链接清理完成"
    echo ""
fi

# 资源根目录（脚本位于 bash/ 子目录，需向上一级）
HARNESS_HOME="$(cd "$(dirname "$0")/.." && pwd)"

echo "🔧 AI Harness Engineering - CLI 工具配置向导"
echo "============================================"
echo "📂 资源根目录: $HARNESS_HOME"
echo "🎯 OpenCode 配置目录: $OPENCODE_CONFIG"
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
    
    # 尝试符号链接，失败则降级复制
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
# 2. Claude Code 配置
# ==========================================
if command -v claude &> /dev/null; then
    echo "✅ 检测到 Claude Code"
    mkdir -p "$CLAUDE_CONFIG/skills" "$CLAUDE_CONFIG/agents" "$CLAUDE_CONFIG/commands"

    safe_link "$HARNESS_HOME/skills/templates"    "$CLAUDE_CONFIG/skills/harness-templates"
    safe_link "$HARNESS_HOME/skills/schemas"      "$CLAUDE_CONFIG/skills/harness-schemas"
    safe_link "$HARNESS_HOME/skills/checklists"   "$CLAUDE_CONFIG/skills/harness-checklists"

    for agent_file in "$HARNESS_HOME/agents/subagents"/*.md "$HARNESS_HOME/agents/independent"/*.md; do
        [ -f "$agent_file" ] || continue
        agent_name=$(basename "$agent_file" .md)
        safe_link "$agent_file" "$CLAUDE_CONFIG/agents/harness-$agent_name.md"
    done

    [ -f "$HARNESS_HOME/commands/harness-new.md" ] && \
        safe_link "$HARNESS_HOME/commands/harness-new.md" "$CLAUDE_CONFIG/commands/harness-new.md"
    [ -f "$HARNESS_HOME/commands/harness-iterate.md" ] && \
        safe_link "$HARNESS_HOME/commands/harness-iterate.md" "$CLAUDE_CONFIG/commands/harness-iterate.md"

    echo "   → Claude Code 配置完成"
fi

# ==========================================
# 3. OpenCode 配置
# ==========================================
if command -v opencode &> /dev/null; then
    echo "✅ 检测到 OpenCode"
    mkdir -p "$OPENCODE_CONFIG/agents" "$OPENCODE_CONFIG/skills"

    # Skills
    safe_link "$HARNESS_HOME/skills/templates"   "$OPENCODE_CONFIG/skills/harness-templates"
    safe_link "$HARNESS_HOME/skills/schemas"     "$OPENCODE_CONFIG/skills/harness-schemas"
    safe_link "$HARNESS_HOME/skills/checklists"  "$OPENCODE_CONFIG/skills/harness-checklists"

    # Agents - 扫描所有可能的目录（subagents / independent / agents根目录）
    for agent_file in \
        "$HARNESS_HOME/agents/subagents"/*.md \
        "$HARNESS_HOME/agents/independent"/*.md \
        "$HARNESS_HOME/agents"/*.md; do
        
        [ -f "$agent_file" ] || continue
        agent_name=$(basename "$agent_file" .md)
        # 避免重复安装同名文件
        [ -e "$OPENCODE_CONFIG/agents/harness-$agent_name.md" ] && continue
        safe_link "$agent_file" "$OPENCODE_CONFIG/agents/harness-$agent_name.md"
    done

    echo "   → OpenCode 配置完成"
else
    echo "⚠️  未检测到 opencode 命令，跳过 OpenCode 配置"
    echo "   如需手动安装，请确认 opencode 已加入 PATH"
fi

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
    echo "      find \"$HARNESS_HOME\" -name \"*.md\" -path \"*/agents/*\""
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