import logging
from src.lighter_api import LighterAPI
import asyncio

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HedgePair:
    """对冲交易对"""
    
    def __init__(self, account_long, account_short, config):
        """
        初始化对冲交易对
        
        Args:
            account_long (dict): 做多账户信息
            account_short (dict): 做空账户信息
            config (dict): 配置信息
        """
        self.account_long = account_long
        self.account_short = account_short
        self.config = config
        self.pair_id = f"{account_long['account_name']}-{account_short['account_name']}"
        
        # 获取代理池
        proxy_pool = config.get('proxy_pool', [])
        proxy_pool_dict = {proxy['name']: proxy for proxy in proxy_pool}
        
        # 为做多账户初始化API客户端
        long_proxy_name = account_long.get('proxy')
        long_proxy_config = proxy_pool_dict.get(long_proxy_name) if long_proxy_name else None
        self.api_long = LighterAPI(
            api_key=account_long['api_key'],
            network=account_long.get('network', 'mainnet'),
            proxy_config=long_proxy_config,
            account_index=account_long.get('account_index', 0),
            api_key_index=account_long.get('api_key_index', 0)
        )
        
        # 为做空账户初始化API客户端
        short_proxy_name = account_short.get('proxy')
        short_proxy_config = proxy_pool_dict.get(short_proxy_name) if short_proxy_name else None
        self.api_short = LighterAPI(
            api_key=account_short['api_key'],
            network=account_short.get('network', 'mainnet'),
            proxy_config=short_proxy_config,
            account_index=account_short.get('account_index', 0),
            api_key_index=account_short.get('api_key_index', 0)
        )
        
        # 交易参数
        self.symbol = config['trading_pair']
        self.leverage = config['leverage']
        self.position_size = config['position_size']
        self.market_index = None  # 将通过动态查找确定
        
        # 订单信息
        self.order_long = None
        self.order_short = None
        
        logger.info(f"创建对冲交易对: {self.pair_id}")

    async def initialize(self):
        """
        异步初始化对冲交易对
        """
        await self._initialize_market_id()

    async def _initialize_market_id(self):
        """
        初始化市场ID
        """
        try:
            logger.info(f"查找交易对 {self.symbol} 的市场信息...")
            
            # 使用做多账户查找市场信息（两个账户应该在同一网络，所以市场ID相同）
            market_result = await self.api_long.find_market_by_symbol(self.symbol)
            
            if market_result.get('success', False):
                self.market_index = market_result['market_id']
                market_info = market_result['market_info']
                logger.info(f"✓ 找到交易对 {self.symbol}，市场ID: {self.market_index}")
                logger.info(f"  市场状态: {market_info.status}")
                logger.info(f"  最小基础数量: {market_info.min_base_amount}")
                logger.info(f"  最小报价数量: {market_info.min_quote_amount}")
            else:
                logger.error(f"✗ 查找交易对失败: {market_result.get('error', '未知错误')}")
                # 如果查找失败，使用默认值0作为fallback
                self.market_index = 0
                logger.warning(f"使用默认市场索引: {self.market_index}")
                
        except Exception as e:
            logger.error(f"初始化市场ID失败: {e}")
            # 如果发生异常，使用默认值0作为fallback
            self.market_index = 0
            logger.warning(f"使用默认市场索引: {self.market_index}")

    async def open_positions(self):
        """
        开仓建立对冲头寸
        """
        try:
            # 检查是否已初始化market_index
            if self.market_index is None:
                logger.error(f"未初始化market_index，无法开仓 {self.pair_id}")
                return False
            
            # 将USD金额转换为交易对数量
            logger.info(f"将USD金额 {self.position_size} USD 转换为 {self.symbol} 数量...")
            
            # 使用做多账户进行转换（两个账户应该在同一网络，所以价格相同）
            quantity_result = await self.api_long.usd_to_quantity(self.market_index, self.position_size)
            
            if not quantity_result.get('success', False):
                logger.error(f"USD到数量转换失败: {quantity_result.get('error', '未知错误')}")
                return False
            
            quantity = quantity_result['quantity']
            current_price = quantity_result['price']
            
            logger.info(f"转换结果: {self.position_size} USD = {quantity:.6f} {self.symbol} (价格: {current_price:.2f} USD)")
            
            # 做多账户下单买入
            self.order_long = await self.api_long.place_order(
                market_index=self.market_index,
                side='buy',
                price=None,  # 市价单
                quantity=quantity,
                leverage=self.leverage
            )
            
            # 做空账户下单卖出
            self.order_short = await self.api_short.place_order(
                market_index=self.market_index,
                side='sell',
                price=None,  # 市价单
                quantity=quantity,
                leverage=self.leverage
            )
            
            logger.info(f"对冲头寸已建立: {self.pair_id}")
            logger.info(f"做多订单: {self.order_long}")
            logger.info(f"做空订单: {self.order_short}")
            
            return True
        except Exception as e:
            logger.error(f"开仓失败 {self.pair_id}: {str(e)}")
            return False

    async def get_floating_pnl(self):
        """
        获取浮动盈亏
        
        Returns:
            float: 浮动盈亏值
        """
        try:
            # 检查是否已初始化market_index
            if self.market_index is None:
                logger.error(f"未初始化market_index，无法获取浮动盈亏 {self.pair_id}")
                return 0
            
            # 获取两个账户的持仓信息
            positions_long = await self.api_long.get_open_positions(market_index=self.market_index)
            positions_short = await self.api_short.get_open_positions(market_index=self.market_index)
            
            # 计算总浮动盈亏
            total_pnl = 0
            
            # 累加做多账户的盈亏
            if positions_long and 'positions' in positions_long:
                for position in positions_long['positions']:
                    if position.get('symbol') == self.symbol:
                        pnl_value = position.get('unrealized_pnl', 0)
                        # 确保pnl_value是数字类型
                        if isinstance(pnl_value, str):
                            try:
                                pnl_value = float(pnl_value)
                            except (ValueError, TypeError):
                                pnl_value = 0
                        total_pnl += pnl_value
            
            # 累加做空账户的盈亏
            if positions_short and 'positions' in positions_short:
                for position in positions_short['positions']:
                    if position.get('symbol') == self.symbol:
                        pnl_value = position.get('unrealized_pnl', 0)
                        # 确保pnl_value是数字类型
                        if isinstance(pnl_value, str):
                            try:
                                pnl_value = float(pnl_value)
                            except (ValueError, TypeError):
                                pnl_value = 0
                        total_pnl += pnl_value
            
            return total_pnl
        except Exception as e:
            logger.error(f"获取浮动盈亏失败 {self.pair_id}: {str(e)}")
            return 0

    async def is_stop_loss_triggered(self):
        """
        检查是否触发止损
        
        Returns:
            bool: 是否触发止损
        """
        floating_pnl = await self.get_floating_pnl()
        stop_loss_threshold = self.config['stop_loss_threshold']
        
        # 如果浮动亏损超过阈值，触发止损
        if floating_pnl < -abs(stop_loss_threshold):
            logger.info(f"触发止损 {self.pair_id}: 浮动盈亏 {floating_pnl} USD")
            return True
        
        return False

    async def close_positions(self):
        """
        平仓
        """
        try:
            # 检查是否已初始化market_index
            if self.market_index is None:
                logger.error(f"未初始化market_index，无法平仓 {self.pair_id}")
                return False
            
            # 平仓做多头寸
            # 注意：这里需要订单索引，简化实现使用默认值0
            result_long = await self.api_long.close_position(
                market_index=self.market_index,
                order_index=0
            )
            
            # 平仓做空头寸
            result_short = await self.api_short.close_position(
                market_index=self.market_index,
                order_index=0
            )
            
            logger.info(f"对冲头寸已平仓: {self.pair_id}")
            logger.info(f"做多平仓结果: {result_long}")
            logger.info(f"做空平仓结果: {result_short}")
            
            return True
        except Exception as e:
            logger.error(f"平仓失败 {self.pair_id}: {str(e)}")
            return False