# Web3 对冲交易机器人

这是一个基于Lighter交易所API的对冲交易机器人，可以自动执行对冲交易策略，通过同时在两个账户中建立相反的头寸来降低市场风险。

## 功能特性

- 支持多个账户两两配对进行对冲交易
- 自动开仓建立对冲头寸（一个账户做多，另一个账户做空）
- 实时监控浮动盈亏，当亏损达到阈值时自动平仓
- 支持代理池配置，每个账户可选择不同的代理
- 可配置的交易参数（交易对、杠杆倍数、开仓金额等）
- 支持账户索引和API密钥索引配置
- 通知系统（邮件通知）
- **智能重试机制** - 自动重试临时性API错误
- **结构化错误处理** - 清晰区分查询失败和空结果
- **防重复开仓保护** - 确保API不稳定时不会重复开仓
- **完整的测试套件** - 模拟测试、干运行测试、集成测试
- **USD金额开仓** - 使用USD金额指定开仓规模，自动转换为交易对数量
- **动态精度计算** - 根据市场精度自动计算base_amount
- **最小数量检查** - 自动检查并调整到最小基础数量

## 系统架构

```text
web3-trading-bot/
├── config.yaml              # 配置文件
├── src/
│   ├── lighter_api.py       # Lighter交易所API客户端（带重试机制）
│   ├── config_manager.py    # 配置管理器
│   ├── hedge_trader.py      # 对冲交易核心逻辑
│   ├── notification.py      # 通知系统
│   └── trading_bot.py       # 交易机器人主控制器（防重复开仓）
├── tests/
│   ├── test_lighter_api_mock.py      # API模拟测试
│   ├── test_lighter_api_integration.py # API集成测试
│   ├── test_hedge_trading.py         # 对冲交易测试
│   └── test_config.yaml              # 测试配置
├── docs/
│   └── API_REFERENCE.md              # API参考文档
└── TESTING.md                        # 测试指南
```

## 安装依赖

```bash
# 使用uv安装依赖
uv pip install -r requirements.txt
```

## 配置说明

在 `config.yaml` 文件中配置以下参数：

- `trading_pair`: 交易对（默认BTC）
- `leverage`: 杠杆倍数
- `position_size`: 开仓金额（USD）
- `stop_loss_threshold`: 浮动亏损阈值
- `proxy_pool`: 代理池设置，可配置多个代理
- `notification`: 通知设置
- `api_credentials`: API凭证列表，每个账户包含：
  - `account_name`: 账户名称
  - `api_key`: 私钥
  - `account_index`: 账户索引
  - `api_key_index`: API密钥索引
  - `network`: 网络类型（mainnet/testnet）
  - `proxy`: 使用的代理名称（对应代理池中的代理）

## 使用方法

```bash
# 使用uv运行交易机器人
uv run python src/trading_bot.py
```

## 测试

```bash
# 运行所有测试
uv run python run_tests.py

# 运行模拟测试（推荐）
uv run python tests/test_lighter_api_mock.py

# 运行集成测试（需要配置测试账户）
uv run python tests/test_lighter_api_integration.py

# 运行单元测试
uv run python -m pytest tests/
```

详细测试指南请参考 [TESTING.md](TESTING.md)

## 新功能说明

### 智能重试机制

- **自动重试**: 对临时性API错误（网络超时、限流等）自动重试
- **指数退避**: 重试延迟时间按指数增长（2^0, 2^1, 2^2 秒）
- **错误分类**: 智能区分临时错误和永久错误

### 结构化错误处理

所有API方法返回统一格式：
```python
{
    'success': bool,      # 操作是否成功
    'data': object,       # 成功时的数据
    'error': str,         # 失败时的错误信息
    'timestamp': float    # 时间戳
}
```

### 防重复开仓保护

- **安全检查**: 只在查询成功且确认无持仓时才开仓
- **保守策略**: 查询失败时跳过开仓，避免重复持仓
- **详细通知**: 查询失败时发送紧急通知

## 新功能说明

### USD金额开仓

系统现在支持使用USD金额来指定开仓规模，而不是交易对数量。这提供了更好的用户体验和风险管理：

- **自动转换**: 系统根据当前市场价格自动将USD金额转换为交易对数量
- **最小数量检查**: 自动检查并确保数量满足交易所的最小基础数量要求
- **动态精度**: 根据市场精度自动计算正确的base_amount

示例配置：
```yaml
position_size: 100  # 100 USD
```

### 价格获取安全机制

- **严格错误处理**: 如果无法获取市场价格，系统会立即停止执行而不是使用默认价格
- **明确的错误信息**: 提供清晰的错误信息帮助诊断问题
- **早期错误检测**: 在交易执行前就检测到价格获取问题

### 动态精度计算

系统根据市场信息自动计算正确的精度：

- `base_amount_multiplier = pow(10, market_info.supported_size_decimals)`
- `base_amount = int(quantity * base_amount_multiplier)`

例如：BTC市场支持5位小数精度，则乘数为100,000
- 0.000200 BTC × 100,000 = 20 base_amount

详细API文档请参考 [docs/API_REFERENCE.md](docs/API_REFERENCE.md)