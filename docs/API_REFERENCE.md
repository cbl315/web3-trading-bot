# LighterAPI 参考文档

## 概述

`LighterAPI` 类提供了与 Lighter 交易所交互的统一接口，具有智能重试机制和结构化错误处理。

## 核心特性

- **结构化返回**: 所有方法返回统一格式的结果
- **智能重试**: 自动重试临时性错误
- **错误分类**: 区分临时错误和永久错误
- **安全交易**: 防止重复开仓和状态不一致
- **USD金额开仓**: 使用USD金额指定开仓规模，自动转换为交易对数量
- **动态精度计算**: 根据市场精度自动计算base_amount
- **最小数量检查**: 自动检查并调整到最小基础数量
- **价格获取安全**: 价格获取失败时立即停止执行，避免错误交易

## API 方法

### get_account_info

获取账户信息。

**参数**:
- `account_index` (int, optional): 账户索引，默认为实例配置

**返回**:
```python
{
    'success': bool,           # 查询是否成功
    'account_info': object,    # 账户信息对象
    'error': str or None,      # 错误信息（如果查询失败）
    'timestamp': float         # 查询时间戳
}
```

**示例**:
```python
result = await api.get_account_info()
if result['success']:
    account = result['account_info']
    print(f"账户余额: {account.balance}")
else:
    print(f"查询失败: {result['error']}")
```

### get_open_positions

获取持仓信息。

**参数**:
- `market_index` (int, optional): 市场索引，默认为 0

**返回**:
```python
{
    'success': bool,           # 查询是否成功
    'positions': list,         # 持仓列表
    'error': str or None,      # 错误信息（如果查询失败）
    'timestamp': float         # 查询时间戳
}
```

**持仓数据结构**:
```python
{
    'market_id': str,          # 市场ID
    'symbol': str,             # 交易对符号
    'side': str,               # 方向 ('long'/'short')
    'position': float,         # 持仓量（绝对值）
    'position_raw': float,     # 原始持仓量（带符号）
    'avg_entry_price': float,  # 平均入场价格
    'unrealized_pnl': float,   # 未实现盈亏
    'realized_pnl': float      # 已实现盈亏
}
```

**示例**:
```python
result = await api.get_open_positions()
if result['success']:
    for position in result['positions']:
        print(f"{position['symbol']} {position['side']}: {position['position']}")
else:
    print(f"持仓查询失败: {result['error']}")
```

### place_order

下单交易。

**参数**:
- `market_index` (int): 市场索引
- `side` (str): 方向 ('buy'/'sell')
- `quantity` (float): 数量
- `price` (float, optional): 价格（None 表示市价单）
- `leverage` (float, optional): 杠杆，默认为 1

**返回**:
```python
{
    'success': bool,           # 交易是否成功
    'tx': object,              # 交易对象
    'tx_hash': str,            # 交易哈希
    'error': str or None,      # 错误信息（如果交易失败）
    'timestamp': float         # 交易时间戳
}
```

**注意**: 此方法为关键操作，失败时会抛出 `PermanentAPIError` 异常。

**示例**:
```python
try:
    result = await api.place_order(
        market_index=0,
        side='buy',
        quantity=0.001,
        price=None  # 市价单
    )
    if result['success']:
        print(f"下单成功，交易哈希: {result['tx_hash']}")
except PermanentAPIError as e:
    print(f"下单失败: {e}")
```

### close_position

平仓（取消订单）。

**参数**:
- `market_index` (int): 市场索引
- `order_index` (int): 订单索引

**返回**:
```python
{
    'success': bool,           # 平仓是否成功
    'tx': object,              # 交易对象
    'tx_hash': str,            # 交易哈希
    'error': str or None,      # 错误信息（如果平仓失败）
    'timestamp': float         # 平仓时间戳
}
```

**注意**: 此方法为关键操作，失败时会抛出 `PermanentAPIError` 异常。

### close_all_positions

平仓所有头寸。

**返回**:
```python
{
    'success': bool,           # 平仓是否成功
    'tx': object,              # 交易对象
    'tx_hash': str,            # 交易哈希
    'error': str or None,      # 错误信息（如果平仓失败）
    'timestamp': float         # 平仓时间戳
}
```

**注意**: 此方法为关键操作，失败时会抛出 `PermanentAPIError` 异常。

### get_market_price

获取当前市场价格。

**参数**:
- `market_id` (int): 市场ID

**返回**:
```python
{
    'success': bool,           # 查询是否成功
    'price': float,            # 当前价格
    'error': str or None,      # 错误信息（如果查询失败）
    'timestamp': float         # 查询时间戳
}
```

**注意**: 如果无法获取价格，会返回错误而不是使用默认价格。

### usd_to_quantity

将USD金额转换为交易对数量。

**参数**:
- `market_id` (int): 市场ID
- `usd_amount` (float): USD金额

**返回**:
```python
{
    'success': bool,           # 转换是否成功
    'quantity': float,         # 转换后的数量
    'price': float,            # 使用的价格
    'error': str or None,      # 错误信息（如果转换失败）
    'timestamp': float         # 转换时间戳
}
```

**功能**:
- 自动根据当前市场价格计算数量
- 检查并确保数量满足最小基础数量要求
- 如果价格获取失败，立即返回错误

### get_market_min_base_amount

获取市场的最小基础数量。

**参数**:
- `market_id` (int): 市场ID

**返回**:
```python
{
    'success': bool,           # 查询是否成功
    'min_base_amount': float,  # 最小基础数量
    'error': str or None,      # 错误信息（如果查询失败）
    'timestamp': float         # 查询时间戳
}
```

## 错误处理

### 错误类型

1. **临时性错误** (自动重试)
   - 网络超时、连接问题
   - 交易所限流、负载过高
   - HTTP 502/503/504 错误

2. **永久性错误** (立即失败)
   - 账户权限错误
   - 参数错误
   - 资金不足

### 重试机制

- **最大重试次数**: 3 次
- **重试延迟**: 指数退避策略 (2^0, 2^1, 2^2 秒)
- **错误分类**: 自动识别临时/永久错误

### 错误处理模式

| 操作类型 | 失败处理 | 适用场景 |
|----------|----------|----------|
| 查询操作 | 返回结构化错误 | `get_account_info`, `get_open_positions` |
| 交易操作 | 抛出异常 | `place_order`, `close_position` |

## 使用示例

### 安全持仓检查

```python
async def check_and_open_positions(api_long, api_short, symbol):
    """安全检查持仓并开仓"""
    
    # 检查做多账户持仓
    result_long = await api_long.get_open_positions()
    if not result_long['success']:
        logger.error(f"做多账户查询失败: {result_long['error']}")
        return False
    
    # 检查做空账户持仓
    result_short = await api_short.get_open_positions()
    if not result_short['success']:
        logger.error(f"做空账户查询失败: {result_short['error']}")
        return False
    
    # 检查是否有持仓
    long_has_position = any(
        p['symbol'] == symbol and p['side'] == 'long' and p['position'] > 0
        for p in result_long['positions']
    )
    
    short_has_position = any(
        p['symbol'] == symbol and p['side'] == 'short' and p['position'] > 0
        for p in result_short['positions']
    )
    
    # 只有确认没有持仓时才开仓
    if not long_has_position and not short_has_position:
        try:
            # 执行对冲开仓
            result_long_order = await api_long.place_order(
                market_index=0, side='buy', quantity=0.001
            )
            result_short_order = await api_short.place_order(
                market_index=0, side='sell', quantity=0.001
            )
            
            return result_long_order['success'] and result_short_order['success']
        except PermanentAPIError as e:
            logger.error(f"开仓失败: {e}")
            return False
    
    return True  # 已有持仓，跳过开仓
```

### USD金额开仓示例

```python
async def open_position_with_usd(api, market_id, usd_amount, side='buy'):
    """使用USD金额开仓"""
    
    # 将USD金额转换为交易对数量
    conversion_result = await api.usd_to_quantity(market_id, usd_amount)
    
    if not conversion_result['success']:
        logger.error(f"USD转换失败: {conversion_result['error']}")
        return False
    
    quantity = conversion_result['quantity']
    current_price = conversion_result['price']
    
    logger.info(f"转换结果: {usd_amount} USD = {quantity:.6f} (价格: {current_price:.2f} USD)")
    
    try:
        # 下单
        order_result = await api.place_order(
            market_index=market_id,
            side=side,
            quantity=quantity,
            price=None,  # 市价单
            leverage=1,
            order_type='market'
        )
        
        if order_result['success']:
            logger.info(f"下单成功，交易哈希: {order_result['tx_hash']}")
            return True
        else:
            logger.error(f"下单失败: {order_result['error']}")
            return False
            
    except PermanentAPIError as e:
        logger.error(f"下单异常: {e}")
        return False
```

### 错误监控

```python
async def monitor_api_health(api):
    """监控 API 健康状态"""
    
    # 测试账户信息查询
    account_result = await api.get_account_info()
    if not account_result['success']:
        logger.warning(f"账户查询异常: {account_result['error']}")
        return False
    
    # 测试持仓查询
    positions_result = await api.get_open_positions()
    if not positions_result['success']:
        logger.warning(f"持仓查询异常: {positions_result['error']}")
        return False
    
    return True
```

## 配置参数

### LighterAPI 初始化参数

- `api_key` (str): API 密钥
- `network` (str): 网络类型 ('mainnet'/'testnet')
- `proxy_config` (dict, optional): 代理配置
- `account_index` (int, optional): 账户索引，默认为 0
- `api_key_index` (int, optional): API 密钥索引，默认为 0

### 重试配置

- `max_retries` (int): 最大重试次数，默认为 3
- `retry_delay_base` (int): 基础延迟秒数，默认为 2

## 最佳实践

1. **始终检查 success 字段**
   ```python
   result = await api.get_open_positions()
   if not result['success']:
       # 处理错误
       return
   ```

2. **使用 try-except 处理交易操作**
   ```python
   try:
       result = await api.place_order(...)
   except PermanentAPIError as e:
       # 处理交易失败
   ```

3. **实现防重复开仓逻辑**
   - 查询成功且确认无持仓时才开仓
   - 查询失败时跳过开仓操作

4. **监控 API 健康状态**
   - 定期测试查询操作
   - 记录错误频率和类型
   - 设置告警阈值

5. **使用USD金额开仓**
   - 使用USD金额而不是交易对数量来指定开仓规模
   - 系统会自动处理价格转换和最小数量检查
   - 提供更好的风险管理和用户体验

6. **处理价格获取失败**
   - 价格获取失败时立即停止执行
   - 不要使用硬编码的默认价格
   - 提供清晰的错误信息帮助诊断问题

## 故障排除

### 常见问题

1. **查询总是返回空结果**
   - 检查账户索引是否正确
   - 验证网络连接和代理配置
   - 确认 API 密钥权限

2. **重试机制不工作**
   - 检查错误消息是否被识别为临时错误
   - 验证重试配置参数
   - 查看详细日志输出

3. **交易操作频繁失败**
   - 检查资金余额
   - 验证交易参数
   - 确认市场状态

### 调试技巧

启用详细日志:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

检查重试过程:
```python
# 观察日志中的重试信息
# "获取持仓信息 临时失败 (尝试 1/3): timeout"
# "获取持仓信息 在第2次重试后成功"
```