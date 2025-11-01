import logging
import lighter
import asyncio
import aiohttp
from typing import Callable, Any

class APIError(Exception):
    """API错误基类"""
    pass

class TemporaryAPIError(APIError):
    """临时性API错误（可重试）"""
    pass

class PermanentAPIError(APIError):
    """永久性API错误（不可重试）"""
    pass

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LighterAPI:
    def __init__(self, api_key, network='mainnet', proxy_config=None, account_index=0, api_key_index=0):
        self.api_key = api_key
        self.network = network
        self.account_index = account_index
        self.api_key_index = api_key_index
        
        # 根据网络设置基础URL，不支持直接指定URL
        if network == 'mainnet':
            self.base_url = "https://mainnet.zklighter.elliot.ai"
        elif network == 'testnet':
            self.base_url = "https://testnet.zklighter.elliot.ai"
        else:
            raise ValueError(f"不支持的网络类型: {network}，仅支持 'mainnet' 或 'testnet'")
            
        # 设置代理配置
        self.proxy_config = proxy_config
        
        # 初始化客户端将在首次API调用时进行
        self.client = None
        
        # 重试配置
        self.max_retries = 3
        self.retry_delay_base = 2  # 基础延迟秒数
        
        # 基础数量乘数（将在获取市场信息时设置）
        self.base_amount_multiplier = None
    
    async def _call_with_retry(self, api_func: Callable, operation_name: str, 
                              is_critical: bool = True) -> Any:
        """
        带重试机制的API调用
        
        Args:
            api_func: 要执行的API函数
            operation_name: 操作名称（用于日志）
            is_critical: 是否为关键操作（失败时抛出异常）
            
        Returns:
            API调用结果
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                result = await api_func()
                if attempt > 0:
                    logger.info(f"{operation_name} 在第{attempt+1}次重试后成功")
                return result
                
            except Exception as e:
                last_error = e
                error_msg = str(e)
                
                # 判断错误类型
                if self._is_temporary_error(error_msg):
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delay_base ** attempt
                        logger.warning(
                            f"{operation_name} 临时失败 (尝试 {attempt+1}/{self.max_retries}): {error_msg}"
                        )
                        logger.info(f"等待 {delay} 秒后重试...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"{operation_name} 重试{self.max_retries}次后仍然失败: {error_msg}"
                        )
                else:
                    # 永久性错误，不重试
                    logger.error(f"{operation_name} 永久性失败: {error_msg}")
                    break
        
        # 所有重试都失败
        error_result = {
            'success': False,
            'error': str(last_error),
            'timestamp': asyncio.get_event_loop().time()
        }
        
        if is_critical:
            # 对于关键操作，仍然抛出异常以保持向后兼容性
            # 但调用方可以选择捕获异常或检查返回结果
            raise PermanentAPIError(f"{operation_name} 失败: {str(last_error)}")
        else:
            logger.error(f"{operation_name} 失败，但允许继续运行: {str(last_error)}")
            return error_result
    
    def _is_temporary_error(self, error_msg: str) -> bool:
        """
        判断是否为临时性错误（可重试）
        
        Args:
            error_msg: 错误消息
            
        Returns:
            bool: 是否为临时性错误
        """
        temporary_indicators = [
            'timeout', 'time out', 'timed out',
            'connection', 'network', 'unavailable',
            'busy', 'overload', 'rate limit',
            'temporary', 'retry', 'try again',
            '502', '503', '504',  # HTTP 错误码
        ]
        
        error_lower = error_msg.lower()
        return any(indicator in error_lower for indicator in temporary_indicators)

    def _initialize_client(self):
        """初始化Lighter客户端"""
        if self.client is not None:
            return
            
        try:
            # 创建配置对象
            config = lighter.Configuration(host=self.base_url)
            
            # 设置代理（如果配置了代理）
            if self.proxy_config:
                proxy_url = f"http://{self.proxy_config['host']}:{self.proxy_config['port']}"
                config.proxy = proxy_url
                logger.info(f"设置代理: {proxy_url}")
                
                # 如果代理配置包含认证信息，设置代理认证头
                if 'username' in self.proxy_config and 'password' in self.proxy_config:
                    auth = aiohttp.BasicAuth(self.proxy_config['username'], self.proxy_config['password'])
                    config.proxy_headers = {'Proxy-Authorization': auth.encode()}
                    logger.info(f"设置代理认证: {self.proxy_config['username']}")
            
            # 创建SignerClient，使用配置文件中的账户索引和API密钥索引
            self.client = lighter.SignerClient(
                url=self.base_url,
                private_key=self.api_key,
                account_index=self.account_index,
                api_key_index=self.api_key_index
            )
            
            # 设置代理（如果需要）
            if self.proxy_config:
                proxy_url = f"http://{self.proxy_config['host']}:{self.proxy_config['port']}"
                self.client.api_client.configuration.proxy = proxy_url
                
                # 如果代理配置包含认证信息，设置代理认证头
                if 'username' in self.proxy_config and 'password' in self.proxy_config:
                    auth = aiohttp.BasicAuth(self.proxy_config['username'], self.proxy_config['password'])
                    self.client.api_client.configuration.proxy_headers = {'Proxy-Authorization': auth.encode()}
                
            logger.info(f"Lighter客户端初始化成功 (账户索引: {self.account_index}, API密钥索引: {self.api_key_index})")
        except Exception as e:
            logger.error(f"Lighter客户端初始化失败: {str(e)}")
            raise

    async def get_account_info(self, account_index=None):
        """
        获取账户信息
        
        Returns:
            dict: {
                'success': bool,           # 查询是否成功
                'account_info': object,    # 账户信息对象
                'error': str or None,      # 错误信息（如果查询失败）
                'timestamp': float         # 查询时间戳
            }
        """
        # 如果没有指定账户索引，使用实例中的账户索引
        if account_index is None:
            account_index = self.account_index
        
        async def _get_account_info():
            self._initialize_client()
            account_api = lighter.AccountApi(self.client.api_client)
            account_info = await account_api.account(by="index", value=str(account_index))
            return {
                'success': True,
                'account_info': account_info,
                'error': None,
                'timestamp': asyncio.get_event_loop().time()
            }
        
        return await self._call_with_retry(
            _get_account_info, 
            "获取账户信息",
            is_critical=False  # 查询操作，失败时返回错误信息
        )

    async def get_open_positions(self, market_index=0):
        """
        获取持仓信息
        
        Returns:
            dict: {
                'success': bool,           # 查询是否成功
                'positions': list,         # 持仓列表
                'error': str or None,      # 错误信息（如果查询失败）
                'timestamp': float         # 查询时间戳
            }
        """
        async def _get_open_positions():
            self._initialize_client()
            
            # 获取账户信息，其中包含持仓信息
            account_result = await self.get_account_info()
            
            # 如果获取账户信息失败
            if not account_result.get('success', False):
                return {
                    'success': False,
                    'positions': [],
                    'error': f"获取账户信息失败: {account_result.get('error', '未知错误')}",
                    'timestamp': asyncio.get_event_loop().time()
                }
            
            account_info = account_result['account_info']
            
            # 提取持仓信息
            positions = []
            for account in account_info.accounts:
                for position in account.positions:
                    # 根据position的正负判断方向
                    position_amount = position.position
                    # 确保position_amount是数字类型
                    try:
                        position_amount_num = float(position_amount)
                    except (ValueError, TypeError):
                        position_amount_num = 0.0
                    
                    side = 'long' if position_amount_num > 0 else 'short'
                    
                    positions.append({
                        'market_id': position.market_id,
                        'symbol': position.symbol,
                        'side': side,
                        'position': abs(position_amount_num),  # 持仓量取绝对值
                        'position_raw': position_amount_num,    # 原始持仓量（带符号）
                        'avg_entry_price': position.avg_entry_price,
                        'unrealized_pnl': position.unrealized_pnl,
                        'realized_pnl': position.realized_pnl
                    })
            
            return {
                'success': True,
                'positions': positions,
                'error': None,
                'timestamp': asyncio.get_event_loop().time()
            }
        
        return await self._call_with_retry(
            _get_open_positions,
            "获取持仓信息",
            is_critical=False  # 查询操作，失败时返回错误信息
        )

    async def place_order(self, market_index, side, quantity, price=None, leverage=1, order_type='market'):
        """
        下单交易
        
        Args:
            market_index: 市场索引
            side: 订单方向 ('buy' 或 'sell')
            quantity: 数量
            price: 价格（限价单需要，市价单为None）
            leverage: 杠杆
            order_type: 订单类型 ('market' 或 'limit')
            
        Returns:
            dict: {
                'success': bool,           # 交易是否成功
                'tx': object,              # 交易对象
                'tx_hash': str,            # 交易哈希
                'error': str or None,      # 错误信息（如果交易失败）
                'timestamp': float         # 交易时间戳
            }
        """
        async def _place_order():
            self._initialize_client()
            
            # 确定订单方向
            is_ask = (side.lower() == 'sell')
            
            # 根据订单类型决定下单方式
            if order_type.lower() == 'market':
                # 市价单
                # 对于市价单，avg_execution_price 应该设置为一个合理的值
                # 使用 1 作为默认值，避免 "OrderPrice should not be less than 1" 错误
                
                # 使用基础数量乘数计算base_amount
                if self.base_amount_multiplier is None:
                    # 如果没有设置乘数，使用默认值
                    base_amount_multiplier = 1000000
                else:
                    base_amount_multiplier = self.base_amount_multiplier
                
                tx, tx_hash, err = await self.client.create_market_order(
                    market_index=market_index,
                    client_order_index=0,  # 简化实现，实际应使用唯一索引
                    base_amount=int(quantity * base_amount_multiplier),  # 转换为整数单位
                    avg_execution_price=1,  # 市价单使用最小价格值
                    is_ask=is_ask
                )
            elif order_type.lower() == 'limit':
                # 限价单
                if price is None:
                    return {
                        'success': False,
                        'tx': None,
                        'tx_hash': None,
                        'error': "限价单必须指定价格",
                        'timestamp': asyncio.get_event_loop().time()
                    }
                
                # 价格转换：根据市场精度转换价格
                # 由于 supported_price_decimals=2，我们使用 100 作为转换因子
                price_int = int(price * 100)
                
                # 验证价格是否有效
                if price_int < 1:
                    return {
                        'success': False,
                        'tx': None,
                        'tx_hash': None,
                        'error': f"下单失败: 价格 {price} 转换后为 {price_int}，必须大于等于 1",
                        'timestamp': asyncio.get_event_loop().time()
                    }
                
                # 使用基础数量乘数计算base_amount
                if self.base_amount_multiplier is None:
                    # 如果没有设置乘数，使用默认值
                    base_amount_multiplier = 1000000
                else:
                    base_amount_multiplier = self.base_amount_multiplier
                
                tx, tx_hash, err = await self.client.create_order(
                    market_index=market_index,
                    client_order_index=0,  # 简化实现，实际应使用唯一索引
                    base_amount=int(quantity * base_amount_multiplier),  # 转换为整数单位
                    price=price_int,  # 使用转换后的整数价格
                    is_ask=is_ask,
                    order_type=lighter.SignerClient.ORDER_TYPE_LIMIT,
                    time_in_force=lighter.SignerClient.ORDER_TIME_IN_FORCE_GOOD_TILL_TIME,
                    reduce_only=False,
                    trigger_price=0
                )
            else:
                return {
                    'success': False,
                    'tx': None,
                    'tx_hash': None,
                    'error': f"不支持的订单类型: {order_type}",
                    'timestamp': asyncio.get_event_loop().time()
                }
            
            if err:
                return {
                    'success': False,
                    'tx': None,
                    'tx_hash': None,
                    'error': f"下单失败: {err}",
                    'timestamp': asyncio.get_event_loop().time()
                }
                
            return {
                'success': True,
                'tx': tx,
                'tx_hash': tx_hash,
                'error': None,
                'timestamp': asyncio.get_event_loop().time()
            }
        
        return await self._call_with_retry(
            _place_order,
            "下单交易",
            is_critical=True  # 交易操作，失败时返回错误信息
        )

    async def close_position(self, market_index, order_index):
        """
        平仓（取消订单）
        
        Returns:
            dict: {
                'success': bool,           # 平仓是否成功
                'tx': object,              # 交易对象
                'tx_hash': str,            # 交易哈希
                'error': str or None,      # 错误信息（如果平仓失败）
                'timestamp': float         # 平仓时间戳
            }
        """
        async def _close_position():
            self._initialize_client()
            
            # 取消订单来平仓
            tx, tx_hash, err = await self.client.cancel_order(
                market_index=market_index,
                order_index=order_index
            )
            
            if err:
                return {
                    'success': False,
                    'tx': None,
                    'tx_hash': None,
                    'error': f"平仓失败: {err}",
                    'timestamp': asyncio.get_event_loop().time()
                }
                
            return {
                'success': True,
                'tx': tx,
                'tx_hash': tx_hash,
                'error': None,
                'timestamp': asyncio.get_event_loop().time()
            }
        
        return await self._call_with_retry(
            _close_position,
            "平仓操作",
            is_critical=True  # 交易操作，失败时返回错误信息
        )

    async def get_order_book(self, market_id=0):
        """
        获取订单簿信息，了解价格格式
        
        Returns:
            dict: {
                'success': bool,           # 查询是否成功
                'order_book': object,      # 订单簿对象
                'error': str or None,      # 错误信息（如果查询失败）
                'timestamp': float         # 查询时间戳
            }
        """
        async def _get_order_book():
            self._initialize_client()
            order_api = lighter.OrderApi(self.client.api_client)
            order_book = await order_api.order_books(market_id=market_id)
            return {
                'success': True,
                'order_book': order_book,
                'error': None,
                'timestamp': asyncio.get_event_loop().time()
            }
        
        return await self._call_with_retry(
            _get_order_book,
            "获取订单簿",
            is_critical=False  # 查询操作，失败时返回错误信息
        )

    async def get_all_order_books(self):
        """
        获取所有订单簿信息
        
        Returns:
            dict: {
                'success': bool,           # 查询是否成功
                'order_books': object,     # OrderBooks对象
                'error': str or None,      # 错误信息（如果查询失败）
                'timestamp': float         # 查询时间戳
            }
        """
        async def _get_all_order_books():
            self._initialize_client()
            order_api = lighter.OrderApi(self.client.api_client)
            order_books = await order_api.order_books()  # 不指定market_id获取所有
            return {
                'success': True,
                'order_books': order_books,
                'error': None,
                'timestamp': asyncio.get_event_loop().time()
            }
        
        return await self._call_with_retry(
            _get_all_order_books,
            "获取所有订单簿",
            is_critical=False  # 查询操作，失败时返回错误信息
        )

    async def get_market_price(self, market_id):
        """
        获取当前市场价格
        
        Args:
            market_id: 市场ID
            
        Returns:
            dict: {
                'success': bool,           # 查询是否成功
                'price': float,            # 当前价格
                'error': str or None,      # 错误信息（如果查询失败）
                'timestamp': float         # 查询时间戳
            }
        """
        async def _get_market_price():
            self._initialize_client()
            order_api = lighter.OrderApi(self.client.api_client)
            
            # 获取订单簿信息，从中提取当前价格
            order_books_result = await order_api.order_books(market_id=market_id)
            
            # 从订单簿中获取最佳买价和卖价
            if hasattr(order_books_result, 'order_books') and order_books_result.order_books:
                market_order_book = order_books_result.order_books[0]
                
                # 检查是否有价格信息
                # 注意：Lighter API的订单簿可能不包含实时价格数据
                # 如果无法获取实时价格，返回错误而不是使用默认价格
                
                # 尝试从订单簿中提取价格信息
                if hasattr(market_order_book, 'bids') and market_order_book.bids:
                    # 如果有买盘数据，尝试获取最佳买价
                    best_bid = float(market_order_book.bids[0].price)
                    best_ask = float(market_order_book.asks[0].price)
                    current_price = (best_bid + best_ask) / 2
                    
                    return {
                        'success': True,
                        'price': current_price,
                        'error': None,
                        'timestamp': asyncio.get_event_loop().time()
                    }
                else:
                    # 如果订单簿中没有价格信息，返回错误
                    return {
                        'success': False,
                        'price': 0,
                        'error': "订单簿中没有价格信息",
                        'timestamp': asyncio.get_event_loop().time()
                    }
            
            return {
                'success': False,
                'price': 0,
                'error': "无法获取市场价格",
                'timestamp': asyncio.get_event_loop().time()
            }
        
        return await self._call_with_retry(
            _get_market_price,
            f"获取市场 {market_id} 价格",
            is_critical=False
        )

    async def find_market_by_symbol(self, symbol):
        """
        通过交易对符号查找市场信息
        
        Args:
            symbol: 交易对符号 (如 "BTC", "ETH")
            
        Returns:
            dict: {
                'success': bool,           # 查询是否成功
                'market_info': object,     # 市场信息对象
                'market_id': int,          # 市场ID
                'error': str or None,      # 错误信息（如果查询失败）
                'timestamp': float         # 查询时间戳
            }
        """
        async def _find_market_by_symbol():
            self._initialize_client()
            
            # 获取所有订单簿
            order_books_result = await self.get_all_order_books()
            if not order_books_result.get('success', False):
                return {
                    'success': False,
                    'market_info': None,
                    'market_id': None,
                    'error': f"获取订单簿失败: {order_books_result.get('error', '未知错误')}",
                    'timestamp': asyncio.get_event_loop().time()
                }
            
            order_books_obj = order_books_result.get('order_books')
            
            # 检查order_books对象是否有order_books属性
            if hasattr(order_books_obj, 'order_books') and order_books_obj.order_books:
                order_books_list = order_books_obj.order_books
                
                # 查找匹配的交易对
                target_symbol = symbol.upper()
                for order_book in order_books_list:
                    if hasattr(order_book, 'symbol') and order_book.symbol.upper() == target_symbol:
                        # 设置基础数量乘数
                        if hasattr(order_book, 'supported_size_decimals'):
                            self.base_amount_multiplier = pow(10, order_book.supported_size_decimals)
                        else:
                            # 如果没有supported_size_decimals属性，使用默认值
                            self.base_amount_multiplier = 1000000
                        
                        return {
                            'success': True,
                            'market_info': order_book,
                            'market_id': order_book.market_id,
                            'error': None,
                            'timestamp': asyncio.get_event_loop().time()
                        }
                
                # 如果没有找到匹配的交易对
                available_symbols = [ob.symbol for ob in order_books_list if hasattr(ob, 'symbol')]
                return {
                    'success': False,
                    'market_info': None,
                    'market_id': None,
                    'error': f"未找到交易对 '{symbol}'，可用交易对: {', '.join(available_symbols)}",
                    'timestamp': asyncio.get_event_loop().time()
                }
            else:
                return {
                    'success': False,
                    'market_info': None,
                    'market_id': None,
                    'error': "订单簿数据为空或格式不正确",
                    'timestamp': asyncio.get_event_loop().time()
                }
        
        return await self._call_with_retry(
            _find_market_by_symbol,
            f"查找交易对 {symbol}",
            is_critical=False  # 查询操作，失败时返回错误信息
        )

    async def get_market_min_base_amount(self, market_id):
        """
        获取市场的最小基础数量
        
        Args:
            market_id: 市场ID
            
        Returns:
            dict: {
                'success': bool,           # 查询是否成功
                'min_base_amount': float,  # 最小基础数量
                'error': str or None,      # 错误信息（如果查询失败）
                'timestamp': float         # 查询时间戳
            }
        """
        try:
            # 获取所有订单簿信息
            order_books_result = await self.get_all_order_books()
            
            if not order_books_result.get('success', False):
                return {
                    'success': False,
                    'min_base_amount': 0,
                    'error': f"获取订单簿失败: {order_books_result.get('error', '未知错误')}",
                    'timestamp': asyncio.get_event_loop().time()
                }
            
            order_books_obj = order_books_result.get('order_books')
            
            # 查找指定市场ID的订单簿
            if hasattr(order_books_obj, 'order_books') and order_books_obj.order_books:
                for order_book in order_books_obj.order_books:
                    if hasattr(order_book, 'market_id') and order_book.market_id == market_id:
                        if hasattr(order_book, 'min_base_amount'):
                            return {
                                'success': True,
                                'min_base_amount': float(order_book.min_base_amount),
                                'error': None,
                                'timestamp': asyncio.get_event_loop().time()
                            }
            
            return {
                'success': False,
                'min_base_amount': 0,
                'error': f"未找到市场 {market_id} 的最小基础数量信息",
                'timestamp': asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            return {
                'success': False,
                'min_base_amount': 0,
                'error': f"获取最小基础数量失败: {str(e)}",
                'timestamp': asyncio.get_event_loop().time()
            }

    async def usd_to_quantity(self, market_id, usd_amount):
        """
        将USD金额转换为交易对数量
        
        Args:
            market_id: 市场ID
            usd_amount: USD金额
            
        Returns:
            dict: {
                'success': bool,           # 转换是否成功
                'quantity': float,         # 转换后的数量
                'price': float,            # 使用的价格
                'error': str or None,      # 错误信息（如果转换失败）
                'timestamp': float         # 转换时间戳
            }
        """
        try:
            # 获取当前市场价格
            price_result = await self.get_market_price(market_id)
            
            if not price_result.get('success', False):
                return {
                    'success': False,
                    'quantity': 0,
                    'price': 0,
                    'error': f"无法获取市场价格: {price_result.get('error', '未知错误')}",
                    'timestamp': asyncio.get_event_loop().time()
                }
            
            current_price = price_result['price']
            
            # 计算数量：数量 = USD金额 / 价格
            quantity = usd_amount / current_price
            
            # 检查数量是否满足最小基础数量要求
            min_base_result = await self.get_market_min_base_amount(market_id)
            if min_base_result.get('success', False):
                min_base_amount = min_base_result['min_base_amount']
                
                if quantity < min_base_amount:
                    # 如果计算的数量小于最小基础数量，调整到最小基础数量
                    adjusted_quantity = min_base_amount
                    adjusted_usd_amount = adjusted_quantity * current_price
                    
                    logger.warning(f"计算数量 {quantity:.6f} 小于最小基础数量 {min_base_amount:.6f}")
                    logger.warning(f"将数量调整为最小基础数量: {adjusted_quantity:.6f}")
                    logger.warning(f"对应的USD金额: {adjusted_usd_amount:.2f} USD")
                    
                    quantity = adjusted_quantity
            
            return {
                'success': True,
                'quantity': quantity,
                'price': current_price,
                'error': None,
                'timestamp': asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            return {
                'success': False,
                'quantity': 0,
                'price': 0,
                'error': f"USD到数量转换失败: {str(e)}",
                'timestamp': asyncio.get_event_loop().time()
            }

    async def get_active_orders(self, account_index=None, market_id=0):
        """
        获取活跃订单列表
        
        Returns:
            dict: {
                'success': bool,           # 查询是否成功
                'orders': list,            # 订单列表
                'error': str or None,      # 错误信息（如果查询失败）
                'timestamp': float         # 查询时间戳
            }
        """
        async def _get_active_orders():
            self._initialize_client()
            
            # 如果没有指定账户索引，使用实例中的账户索引
            target_account_index = account_index if account_index is not None else self.account_index
            
            order_api = lighter.OrderApi(self.client.api_client)
            active_orders = await order_api.account_active_orders(
                account_index=target_account_index,
                market_id=market_id
            )
            
            return {
                'success': True,
                'orders': active_orders,
                'error': None,
                'timestamp': asyncio.get_event_loop().time()
            }
        
        return await self._call_with_retry(
            _get_active_orders,
            "获取活跃订单",
            is_critical=False  # 查询操作，失败时返回错误信息
        )

    async def close_all_positions(self):
        """
        平仓所有头寸
        
        Returns:
            dict: {
                'success': bool,           # 平仓是否成功
                'tx': object,              # 交易对象
                'tx_hash': str,            # 交易哈希
                'error': str or None,      # 错误信息（如果平仓失败）
                'timestamp': float         # 平仓时间戳
            }
        """
        async def _close_all_positions():
            self._initialize_client()
            
            # 取消所有订单
            tx, tx_hash, err = await self.client.cancel_all_orders(
                time_in_force=lighter.SignerClient.CANCEL_ALL_TIF_IMMEDIATE,
                time=0
            )
            
            if err:
                return {
                    'success': False,
                    'tx': None,
                    'tx_hash': None,
                    'error': f"平仓所有头寸失败: {err}",
                    'timestamp': asyncio.get_event_loop().time()
                }
                
            return {
                'success': True,
                'tx': tx,
                'tx_hash': tx_hash,
                'error': None,
                'timestamp': asyncio.get_event_loop().time()
            }
        
        return await self._call_with_retry(
            _close_all_positions,
            "平仓所有头寸",
            is_critical=True  # 交易操作，失败时返回错误信息
        )

    async def close(self):
        """
        关闭客户端连接，清理资源
        """
        if self.client is not None:
            try:
                await self.client.close()
                logger.info("Lighter客户端连接已关闭")
            except Exception as e:
                logger.warning(f"关闭Lighter客户端连接时出错: {e}")
            finally:
                self.client = None

    def __del__(self):
        """
        析构函数，确保资源被清理
        """
        if self.client is not None:
            # 在析构时尝试关闭连接，但最好显式调用close()
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，创建任务来关闭连接
                    loop.create_task(self.close())
                else:
                    # 如果事件循环未运行，直接运行
                    loop.run_until_complete(self.close())
            except Exception:
                # 析构函数中忽略所有异常
                pass
