# LighterAPI 测试指南

## 概述

本文档提供测试 `LighterAPI` 类的完整指南，包括安全测试方法和模拟测试。

## 测试方法

### 1. 模拟测试（推荐）

**适用场景**: 测试代码逻辑，不连接真实API

```bash
# 运行模拟测试
uv run python tests/test_lighter_api_mock.py
```

**特点**:
- 不连接真实交易所
- 测试所有方法逻辑
- 包含错误处理测试
- 快速安全

### 2. 干运行测试

**适用场景**: 连接真实API但不下单

```bash
# 首先配置测试账户
cp tests/test_config.yaml tests/test_config.yaml
# 编辑 tests/test_config.yaml，填入测试账户私钥

# 运行干运行测试
uv run python tests/test_lighter_api_integration.py
```

**配置要求**:
- 使用测试网络 (`testnet`)
- 配置测试账户私钥
- 设置 `dry_run: true`

### 3. 实际测试（谨慎使用）

**适用场景**: 完整功能测试

```yaml
# 在 tests/test_config.yaml 中设置
test_mode:
  enabled: true
  dry_run: false  # 实际执行交易
  max_test_amount: 10  # 很小的测试金额 (USD)
```

**风险提示**:
- 会实际下单交易
- 使用很小的测试金额
- 仅在测试网络进行

## 测试步骤

### 步骤 1: 准备测试环境

1. 确保项目依赖已安装:
   ```bash
   uv sync
   ```

2. 创建测试配置:
   ```bash
   cp tests/test_config.yaml tests/test_config.yaml
   ```

3. 编辑 `tests/test_config.yaml`:
   - 设置测试账户私钥
   - 确认使用 `testnet`
   - 设置 `dry_run: true`

### 步骤 2: 运行模拟测试

```bash
uv run python tests/test_lighter_api_mock.py
```

### 步骤 3: 运行干运行测试

```bash
uv run python tests/test_lighter_api_integration.py
```

### 步骤 4: 分析测试结果

检查日志输出:
- ✓ 表示测试通过
- ✗ 表示测试失败
- 详细错误信息会显示失败原因

## 测试覆盖的方法

### 核心方法测试

1. **`get_account_info()`** - 获取账户信息
   - 返回结构: `{'success': bool, 'account_info': object, 'error': str, 'timestamp': float}`
   - 区分查询失败和空账户

2. **`get_open_positions()`** - 获取持仓信息
   - 返回结构: `{'success': bool, 'positions': list, 'error': str, 'timestamp': float}`
   - 区分查询失败和空持仓

3. **`place_order()`** - 下单交易
   - 返回结构: `{'success': bool, 'tx': object, 'tx_hash': str, 'error': str, 'timestamp': float}`
   - 关键操作，失败时抛出异常

4. **`close_position()`** - 平仓操作
   - 返回结构: `{'success': bool, 'tx': object, 'tx_hash': str, 'error': str, 'timestamp': float}`
   - 关键操作，失败时抛出异常

5. **错误处理** - API 异常处理
   - 重试机制测试
   - 临时错误 vs 永久错误区分
   - 结构化错误返回

6. **USD到数量转换** - USD金额转换功能
   - `usd_to_quantity()` - 将USD金额转换为交易对数量
   - `get_market_price()` - 获取当前市场价格
   - `get_market_min_base_amount()` - 获取最小基础数量
   - 最小数量检查测试
   - 价格获取失败处理测试

7. **动态精度计算** - base_amount计算
   - `base_amount_multiplier` 设置测试
   - 精度计算正确性测试
   - 不同市场精度兼容性测试

### 测试数据验证

- 持仓方向判断 (`long`/`short`)
- 持仓量计算（绝对值）
- 交易结果状态检查
- 错误消息传递
- 结构化返回验证

### USD转换测试验证

- USD金额到交易对数量转换正确性
- 最小基础数量检查功能
- 价格获取失败时的错误处理
- base_amount计算精度验证
- 不同USD金额的转换测试

## 安全注意事项

### ⚠️ 重要警告

1. **永远不要在生产环境测试**
2. **使用测试网络 (`testnet`)**
3. **设置很小的测试金额**
4. **先运行干运行模式**
5. **备份重要数据**

### 测试网络 vs 主网络

| 特性 | 测试网络 | 主网络 |
|------|----------|--------|
| 资金 | 测试币 | 真实资金 |
| 风险 | 无风险 | 高风险 |
| 用途 | 开发测试 | 生产交易 |

## 故障排除

### 常见问题

1. **配置错误**
   - 检查 `tests/test_config.yaml` 格式
   - 确认私钥格式正确
   - 验证网络设置

2. **连接问题**
   - 检查网络连接
   - 验证代理配置
   - 确认 API 端点可达

3. **权限问题**
   - 验证私钥权限
   - 检查账户索引设置
   - 确认 API 密钥有效

### 调试技巧

1. 启用详细日志:
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

2. 检查 API 响应结构:
   ```python
   result = await api.get_open_positions()
   print(f"Success: {result['success']}")
   print(f"Error: {result.get('error')}")
   print(f"Positions count: {len(result['positions'])}")
   ```

3. 验证错误处理:
   ```python
   if not result['success']:
       logger.error(f"API调用失败: {result['error']}")
   else:
       # 处理成功结果
   ```

4. 检查重试机制:
   ```python
   # 观察日志中的重试信息
   # "获取持仓信息 临时失败 (尝试 1/3): timeout"
   # "获取持仓信息 在第2次重试后成功"
   ```

## 扩展测试

### 添加新测试

1. 在 `tests/test_lighter_api_integration.py` 中添加新测试方法
2. 在 `test_with_mocks()` 中添加模拟测试
3. 更新测试总结输出

### 性能测试

```python
# 添加性能测试
import time

async def test_performance():
    start_time = time.time()
    # 执行多次 API 调用
    end_time = time.time()
    logger.info(f"性能测试: {end_time - start_time:.2f}秒")
```

## 贡献指南

欢迎提交测试改进:

1. 添加新的测试用例
2. 改进错误处理测试
3. 增加边界条件测试
4. 优化测试性能