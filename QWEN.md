# Web3 Trading Bot - QWEN 配置

## 项目信息
- **项目名称**: Web3 Trading Bot
- **项目类型**: 对冲交易机器人
- **包管理器**: uv (Python包管理工具)

## 开发环境

### 使用 uv 管理环境
这个项目使用 `uv` 作为 Python 包管理器：

```bash
# 激活虚拟环境
uv venv
source .venv/bin/activate

# 安装依赖
uv sync

# 运行程序
uv run python src/trading_bot.py

# 运行测试
uv run pytest
```

### 项目依赖
- 依赖管理: `pyproject.toml` + `uv.lock`
- 虚拟环境: `.venv/`
- Python版本: 由 `.python-version` 文件指定

## 账号配对机制

### 配对关系配置
账号配对关系通过 `config.yaml` 中的 `hedge_pairs` 配置：

```yaml
hedge_pairs:
  - pair_name: "pair_1"
    long_account: "account_1"
    short_account: "account_2"
  - pair_name: "pair_2"
    long_account: "account_3"
    short_account: "account_4"
```

### 重启恢复机制
- **配对关系**: 从配置文件加载
- **仓位状态**: 通过 API 从交易所实时获取
- **避免重复开仓**: 启动时检查现有持仓，已有持仓的配对跳过开仓

## 核心功能

1. **多账户管理**: 支持多个交易账户同时操作
2. **对冲交易**: 自动建立做多/做空对冲头寸
3. **止损监控**: 实时监控浮动盈亏，自动止损
4. **代理支持**: 支持 HTTP 代理池配置
5. **通知系统**: 支持邮件通知
6. **USD金额开仓**: 使用USD金额指定开仓规模，自动转换为交易对数量
7. **动态精度计算**: 根据市场精度自动计算base_amount
8. **最小数量检查**: 自动检查并调整到最小基础数量
9. **价格获取安全**: 价格获取失败时立即停止执行，避免错误交易

## 文件结构

```
web3-trading-bot/
├── config.yaml          # 主配置文件
├── pyproject.toml       # 项目配置和依赖
├── uv.lock             # uv 锁文件
├── .python-version     # Python 版本
├── src/                # 源代码
│   ├── trading_bot.py  # 主交易机器人
│   ├── hedge_trader.py # 对冲交易对
│   ├── lighter_api.py  # Lighter API 封装
│   └── config_manager.py
└── tests/              # 测试文件
```