import time
import logging
import asyncio
from src.config_manager import load_config
from src.hedge_trader import HedgePair
from src.notification import NotificationManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HedgeTradingBot:
    """对冲交易机器人主控制器"""
    
    def __init__(self, config_path='config.yaml'):
        """
        初始化对冲交易机器人
        
        Args:
            config_path (str): 配置文件路径
        """
        self.config = load_config(config_path)
        self.notification_manager = NotificationManager(self.config)
        self.hedge_pairs = []
        self.running = False
        
        # 创建对冲交易对
        self._create_hedge_pairs()
        
        logger.info(f"对冲交易机器人初始化完成，共创建 {len(self.hedge_pairs)} 个交易对")

    def _create_hedge_pairs(self):
        """创建对冲交易对（使用配置的配对关系）"""
        api_credentials = self.config['api_credentials']
        hedge_pairs_config = self.config.get('hedge_pairs', [])
        
        # 创建账户名称到账户信息的映射
        account_map = {acc['account_name']: acc for acc in api_credentials}
        
        # 使用配置的配对关系创建交易对
        for pair_config in hedge_pairs_config:
            long_account_name = pair_config['long_account']
            short_account_name = pair_config['short_account']
            pair_name = pair_config['pair_name']
            
            # 验证账户是否存在
            if long_account_name not in account_map:
                logger.error(f"配置错误: 做多账户 '{long_account_name}' 不存在")
                continue
            if short_account_name not in account_map:
                logger.error(f"配置错误: 做空账户 '{short_account_name}' 不存在")
                continue
            
            account_long = account_map[long_account_name]
            account_short = account_map[short_account_name]
            
            hedge_pair = HedgePair(account_long, account_short, self.config)
            self.hedge_pairs.append(hedge_pair)
            
            logger.info(f"创建对冲交易对: {pair_name} ({long_account_name} <-> {short_account_name})")

    def start_trading(self):
        """开始交易"""
        logger.info("开始对冲交易...")
        self.running = True
        
        # 运行异步事件循环
        asyncio.run(self._run_trading_loop())

    async def _run_trading_loop(self):
        """运行交易循环"""
        # 为所有交易对开仓
        await self._open_all_positions()
        
        # 进入监控循环
        await self._monitor_loop()

    async def _open_all_positions(self):
        """为所有交易对开仓（安全版本 - 防止重复开仓）"""
        logger.info("正在安全检查现有持仓状态...")
        
        # 检查每个交易对的持仓状态
        positions_checked = 0
        positions_opened = 0
        query_failures = 0
        
        for pair in self.hedge_pairs:
            positions_checked += 1
            
            # 检查是否已经有持仓（返回是否检测到持仓和结果是否可信）
            has_positions, is_confident = await self._check_pair_positions(pair)
            
            if not is_confident:
                query_failures += 1
                logger.error(f"交易对 {pair.pair_id} 持仓查询不可信，跳过开仓以避免重复持仓")
                # 发送紧急通知
                self.notification_manager.send_notification(
                    "持仓查询失败",
                    f"交易对 {pair.pair_id} 持仓查询失败，无法确定当前持仓状态。已跳过开仓以避免重复持仓风险。"
                )
                continue
            
            if has_positions:
                logger.info(f"交易对 {pair.pair_id} 已有持仓，跳过开仓")
                continue
            
            # 没有持仓且查询可信，执行开仓
            logger.info(f"交易对 {pair.pair_id} 确认没有持仓，正在开仓...")
            success = await pair.open_positions()
            
            if success:
                positions_opened += 1
                logger.info(f"交易对 {pair.pair_id} 开仓成功")
            else:
                logger.error(f"开仓失败: {pair.pair_id}")
                # 发送通知
                self.notification_manager.send_notification(
                    "开仓失败",
                    f"交易对 {pair.pair_id} 开仓失败，请检查账户状态和资金情况。"
                )
        
        logger.info(f"安全持仓检查完成: 检查了 {positions_checked} 个交易对，查询失败 {query_failures} 个，新开仓 {positions_opened} 个交易对")
        
        if query_failures > 0:
            self.notification_manager.send_notification(
                "持仓查询总结",
                f"持仓检查完成: 共检查 {positions_checked} 个交易对，其中 {query_failures} 个查询失败已跳过开仓，新开仓 {positions_opened} 个交易对"
            )

    async def _check_pair_positions(self, pair):
        """
        检查交易对是否已经有持仓（改进版本 - 区分查询失败和空持仓）
        
        Args:
            pair: HedgePair对象
            
        Returns:
            tuple: (has_positions: bool, is_confident: bool)
                  has_positions: 是否检测到持仓
                  is_confident: 检查结果是否可信（查询成功）
        """
        try:
            # 获取做多账户的持仓
            result_long = await pair.api_long.get_open_positions(pair.market_index)
            # 获取做空账户的持仓
            result_short = await pair.api_short.get_open_positions(pair.market_index)
            
            # 检查查询是否成功
            if not result_long.get('success', False) or not result_short.get('success', False):
                # 查询失败
                long_error = result_long.get('error', '未知错误')
                short_error = result_short.get('error', '未知错误')
                logger.error(f"持仓查询失败 {pair.pair_id}: 做多账户错误={long_error}, 做空账户错误={short_error}")
                return True, False  # 保守起见认为有持仓，但结果不可信
            
            # 检查数据结构是否完整
            if 'positions' not in result_long or 'positions' not in result_short:
                logger.warning(f"持仓数据结构不完整 {pair.pair_id}")
                return True, False  # 保守起见认为有持仓，但结果不可信
            
            # 检查做多账户是否有做多持仓
            long_has_position = False
            long_position_amount = 0
            for position in result_long['positions']:
                if (position.get('symbol') == pair.symbol and 
                    position.get('side') == 'long'):
                    position_amount = abs(position.get('position', 0))
                    if position_amount > 0:
                        long_has_position = True
                        long_position_amount = position_amount
                        break
            
            # 检查做空账户是否有做空持仓
            short_has_position = False
            short_position_amount = 0
            for position in result_short['positions']:
                if (position.get('symbol') == pair.symbol and 
                    position.get('side') == 'short'):
                    position_amount = abs(position.get('position', 0))
                    if position_amount > 0:
                        short_has_position = True
                        short_position_amount = position_amount
                        break
            
            # 如果两个账户都有对应方向的持仓，则认为已有对冲头寸
            if long_has_position and short_has_position:
                logger.info(f"交易对 {pair.pair_id} 检测到完整对冲头寸 (做多: {long_position_amount}, 做空: {short_position_amount})")
                return True, True
            elif long_has_position or short_has_position:
                # 只有一个账户有持仓，需要告警
                logger.warning(f"交易对 {pair.pair_id} 持仓不完整: 做多账户持仓={long_has_position} ({long_position_amount}), 做空账户持仓={short_has_position} ({short_position_amount})")
                self.notification_manager.send_notification(
                    "持仓不完整警告",
                    f"交易对 {pair.pair_id} 持仓不完整，请手动检查。做多账户持仓: {long_has_position} ({long_position_amount}), 做空账户持仓: {short_has_position} ({short_position_amount})"
                )
                # 这种情况下也返回True，避免重复开仓
                return True, True
            else:
                # 两个账户都没有持仓（查询成功且确认没有持仓）
                logger.info(f"交易对 {pair.pair_id} 确认没有持仓")
                return False, True
                
        except Exception as e:
            logger.error(f"检查持仓状态失败 {pair.pair_id}: {str(e)}")
            # 如果检查失败，保守起见不进行开仓操作
            return True, False

    async def _monitor_loop(self):
        """监控循环"""
        logger.info("进入监控循环...")
        
        while self.running:
            try:
                # 检查每个交易对是否触发止损
                for pair in self.hedge_pairs:
                    if await pair.is_stop_loss_triggered():
                        logger.info(f"交易对 {pair.pair_id} 触发止损，正在平仓...")
                        
                        # 平仓
                        success = await pair.close_positions()
                        
                        if success:
                            # 发送通知
                            self.notification_manager.send_notification(
                                "对冲头寸已平仓",
                                f"交易对 {pair.pair_id} 因触发止损已平仓。"
                            )
                        else:
                            # 发送错误通知
                            self.notification_manager.send_notification(
                                "平仓失败",
                                f"交易对 {pair.pair_id} 平仓失败，请手动处理。"
                            )
                
                # 等待一段时间后继续监控
                await asyncio.sleep(30)  # 每30秒检查一次
                
            except KeyboardInterrupt:
                logger.info("收到停止信号，正在停止交易...")
                self.stop_trading()
                break
            except Exception as e:
                logger.error(f"监控循环发生错误: {str(e)}")
                # 发送错误通知
                self.notification_manager.send_notification(
                    "监控错误",
                    f"监控循环发生错误: {str(e)}"
                )
                # 继续运行而不是停止
                await asyncio.sleep(60)  # 出错后等待1分钟再继续

    def stop_trading(self):
        """停止交易"""
        logger.info("正在停止对冲交易...")
        self.running = False
        
        # 平仓所有头寸
        asyncio.run(self._close_all_positions())
        
        logger.info("对冲交易已停止")

    async def _close_all_positions(self):
        """平仓所有头寸"""
        logger.info("正在平仓所有头寸...")
        
        for pair in self.hedge_pairs:
            success = await pair.close_positions()
            if not success:
                logger.error(f"平仓失败: {pair.pair_id}")
                # 发送通知
                self.notification_manager.send_notification(
                    "平仓失败",
                    f"交易对 {pair.pair_id} 平仓失败，请手动处理。"
                )
        
        logger.info("所有头寸平仓完成")

if __name__ == "__main__":
    try:
        # 创建并启动交易机器人
        bot = HedgeTradingBot()
        bot.start_trading()
    except Exception as e:
        logger.error(f"启动交易机器人时发生错误: {str(e)}")
        # 如果有通知管理器，发送错误通知
        if 'bot' in locals() and hasattr(bot, 'notification_manager'):
            bot.notification_manager.send_notification(
                "机器人启动失败",
                f"启动交易机器人时发生错误: {str(e)}"
            )