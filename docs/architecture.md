# 对冲交易机器人架构设计文档

## 1. 概述

对冲交易机器人是一个基于Lighter交易所API的自动化交易系统，支持多账户轮换和代理池管理。该系统通过配置化的方式管理20个交易账户，使用代理池分散交易请求，实现风险可控的自动化交易。

## 2. 系统架构

### 2.1 整体架构

```mermaid
graph TB
    subgraph "配置管理"
        A[YAML配置] --> B[20个账户管理]
        A --> C[代理池配置]
    end
    
    subgraph "代理池管理"
        D[代理1] --> E[代理轮换]
        F[代理2] --> E
        G[代理3] --> E
    end
    
    subgraph "Lighter API"
        H[账户连接] --> I[订单管理]
        H --> J[持仓查询]
    end
    
    subgraph "对冲交易器"
        K[开仓/平仓] --> L[止损监控]
        K --> M[盈亏计算]
    end
    
    subgraph "交易机器人"
        N[策略执行] --> O[风险控制]
        N --> P[主循环控制]
    end
    
    subgraph "通知系统"
        Q[邮件通知] --> R[状态报告]
        Q --> S[错误警报]
    end
    
    B --> H
    E --> H
    I --> K
    J --> L
    L --> N
    N --> Q
```

### 2.2 模块划分

1. **配置管理模块** (`config_manager.py`)
   - 负责读取和验证YAML配置文件
   - 管理20个交易账户凭证
   - 提供代理池配置访问
   - 验证配置完整性

2. **Lighter API模块** (`lighter_api.py`)
   - 封装Lighter SDK接口
   - 支持HTTP代理轮换
   - 多账户连接管理
   - 订单创建、查询和取消
   - 余额和仓位查询

3. **对冲交易模块** (`hedge_trader.py`)
   - 管理交易对和仓位
   - 执行开仓和平仓操作
   - 实时监控浮动盈亏
   - 自动止损执行
   - 仓位大小计算

4. **通知模块** (`notification.py`)
   - SMTP邮件通知系统
   - 交易状态报告
   - 错误警报发送
   - 支持HTML格式邮件

5. **主控模块** (`trading_bot.py`)
   - 协调各模块工作流程
   - 策略调度和执行
   - 异常处理和恢复
   - 主循环控制

## 3. 数据流设计

### 3.1 初始化流程

```mermaid
flowchart TD
    A[读取YAML配置文件] --> B[初始化代理池管理器]
    B --> C[创建20个Lighter API客户端]
    C --> D[初始化对冲交易管理器]
    D --> E[设置邮件通知系统]
    E --> F[系统就绪]
```

### 3.2 交易流程

```mermaid
flowchart TD
    A[为所有账户执行开仓] --> B[进入监控循环]
    B --> C[定期查询浮动盈亏]
    C --> D{检查止损阈值}
    D -->|未触发| C
    D -->|触发止损| E[自动平仓]
    E --> F[发送交易状态通知]
    F --> G{继续监控?}
    G -->|是| C
    G -->|否| H[结束交易]
```

### 3.3 异常处理流程

```mermaid
flowchart TD
    A[捕获网络异常/API错误] --> B[记录详细错误日志]
    B --> C[发送错误通知邮件]
    C --> D{错误类型判断}
    D -->|可恢复错误| E[等待重试]
    D -->|严重错误| F[安全停止交易]
    E --> G[重新连接]
    G --> H[继续运行]
    F --> I[确保资金安全退出]
```

## 4. 配置设计

### 4.1 配置文件结构

```mermaid
graph TD
    subgraph "交易参数"
        A1[交易对: BTC] --> A2[杠杆倍数: 10]
        A2 --> A3[开仓金额: 0.001 BTC]
        A3 --> A4[止损阈值: 100 USD]
    end
    
    subgraph "代理池配置"
        B1[代理1<br/>127.0.0.1:1080] --> B4[代理轮换]
        B2[代理2<br/>127.0.0.1:1081<br/>认证支持] --> B4
        B3[代理3<br/>127.0.0.1:1082] --> B4
    end
    
    subgraph "通知设置"
        C1[邮件通知<br/>SMTP配置] --> C2[HTML格式报告]
    end
    
    subgraph "API凭证"
        D1[账户1-7<br/>使用代理1] --> D4[20个账户]
        D2[账户8-14<br/>使用代理2] --> D4
        D3[账户15-20<br/>使用代理3] --> D4
    end
    
    B4 --> D4
```

```yaml
# 交易参数
trading_pair: "BTC"           # 交易对
leverage: 10                  # 杠杆倍数
position_size: 0.001          # 开仓金额(BTC)
stop_loss_threshold: 100      # 止损阈值(USD)

# 代理池设置 (3个代理轮换)
proxy_pool:
  - name: "proxy_1"
    host: "127.0.0.1"
    port: 1080
  - name: "proxy_2"
    host: "127.0.0.1"
    port: 1081
    username: "proxy_user_2"
    password: "proxy_password_2"
  - name: "proxy_3"
    host: "127.0.0.1"
    port: 1082

# 通知设置
notification:
  email:
    enabled: false
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    sender: "your_email@gmail.com"
    recipient: "recipient@gmail.com"
    username: "your_email@gmail.com"
    password: "your_app_password"

# API凭证 (20个账户配置)
api_credentials:
  - account_name: "account_1"
    api_key: "your_private_key_1"
    account_index: 0
    api_key_index: 0
    network: "mainnet"
    proxy: "proxy_1"
  - account_name: "account_2"
    api_key: "your_private_key_2"
    account_index: 0
    api_key_index: 0
    network: "mainnet"
    proxy: "proxy_2"
  # ... 共20个账户，轮换使用3个代理
```

## 5. 网络配置

### 5.1 API端点

```mermaid
graph LR
    A[交易机器人] --> B{网络选择}
    B -->|主网| C[mainnet.zklighter.elliot.ai]
    B -->|测试网| D[testnet.zklighter.elliot.ai]
    C --> E[Lighter交易所]
    D --> E
```

系统基于Lighter SDK，支持以下网络类型：
- **主网**: `https://mainnet.zklighter.elliot.ai`
- **测试网**: `https://testnet.zklighter.elliot.ai`

### 5.2 代理池支持

```mermaid
graph TB
    subgraph "代理池"
        A[代理1<br/>1080端口] --> D[代理轮换器]
        B[代理2<br/>1081端口<br/>认证支持] --> D
        C[代理3<br/>1082端口] --> D
    end
    
    subgraph "账户分组"
        E[账户1-7] --> F[使用代理1]
        G[账户8-14] --> H[使用代理2]
        I[账户15-20] --> J[使用代理3]
    end
    
    D --> F
    D --> H
    D --> J
    
    F --> K[Lighter API]
    H --> K
    J --> K
```

系统支持HTTP代理池配置：
- 3个代理服务器轮换使用
- 支持认证代理（用户名/密码）
- 20个账户分散使用不同代理
- 避免单点限制和IP封禁

### 5.3 依赖管理

```mermaid
graph TD
    A[web3-trading-bot] --> B[lighter-sdk]
    A --> C[web3>=7.14.0]
    A --> D[requests>=2.32.5]
    
    B --> E[Lighter交易所API]
    C --> F[区块链交互]
    D --> G[HTTP请求和代理]
```

项目使用uv包管理器，主要依赖：
- `lighter-sdk`: Lighter交易所API
- `web3>=7.14.0`: 区块链交互
- `requests>=2.32.5`: HTTP请求和代理支持

## 6. 核心特性

### 6.1 多账户管理
- 支持20个交易账户同时操作
- 代理池关联分配，避免单点限制
- 账户凭证集中管理

### 6.2 风险管理
- 可配置止损阈值（USD）
- 杠杆倍数控制（1-100倍）
- 仓位大小限制（BTC）
- 实时浮动盈亏监控

### 6.3 代理池轮换
- 3个HTTP代理服务器轮换
- 支持认证代理
- 请求分散化，提高稳定性

### 6.4 通知系统
- SMTP邮件通知
- HTML格式状态报告
- 错误警报和交易确认

## 7. 安全设计

1. **API密钥保护**：私钥存储在配置文件中，建议设置文件权限保护
2. **代理支持**：HTTP代理增强网络匿名性
3. **错误处理**：完善的异常处理机制，防止资金损失
4. **日志记录**：详细的交易和错误日志

## 8. 扩展性设计

1. **模块化设计**：各功能模块解耦，便于独立开发和测试
2. **配置驱动**：通过YAML配置文件控制所有参数
3. **插件化通知**：支持多种通知方式，易于扩展
4. **账户可扩展**：支持更多账户和代理配置