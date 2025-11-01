#!/usr/bin/env python3
"""
LighterAPI 模拟测试脚本
用于在不连接真实API的情况下测试逻辑
"""

import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.lighter_api import LighterAPI

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockLighterAPITester:
    """模拟 LighterAPI 测试器"""
    
    def __init__(self):
        # 创建模拟的 API 密钥和配置
        self.mock_api_key = "mock_private_key_for_testing"
        self.api = LighterAPI(
            api_key=self.mock_api_key,
            network='testnet',
            proxy_config=None
        )
    
    async def test_with_mocks(self):
        """使用模拟对象测试所有方法"""
        logger.info("开始模拟测试 LighterAPI")
        
        # 模拟账户信息
        mock_account_info = Mock()
        mock_account = Mock()
        mock_position = Mock()
        
        # 设置模拟持仓数据
        mock_position.market_id = 0
        mock_position.symbol = "BTC"
        mock_position.position = 0.001  # 做多持仓
        mock_position.avg_entry_price = 50000.0
        mock_position.unrealized_pnl = 100.0
        mock_position.realized_pnl = 50.0
        
        mock_account.positions = [mock_position]
        mock_account_info.accounts = [mock_account]
        
        # 模拟交易结果
        mock_tx = Mock()
        mock_tx_hash = "0xmock_transaction_hash"
        
        # 创建模拟客户端
        mock_client = AsyncMock()
        mock_client.create_market_order = AsyncMock(return_value=(mock_tx, mock_tx_hash, None))
        mock_client.create_order = AsyncMock(return_value=(mock_tx, mock_tx_hash, None))
        mock_client.cancel_order = AsyncMock(return_value=(mock_tx, mock_tx_hash, None))
        mock_client.cancel_all_orders = AsyncMock(return_value=(mock_tx, mock_tx_hash, None))
        
        # 创建模拟 API 客户端
        mock_api_client = Mock()
        mock_api_client.configuration = Mock()
        
        # 将 API 客户端附加到模拟客户端
        mock_client.api_client = mock_api_client
        
        with patch.object(self.api, '_initialize_client') as mock_init, \
             patch('lighter.AccountApi') as mock_account_api_class, \
             patch('lighter.SignerClient', return_value=mock_client):
            
            # 设置模拟返回值
            mock_account_api_instance = AsyncMock()
            mock_account_api_class.return_value = mock_account_api_instance
            mock_account_api_instance.account.return_value = mock_account_info
            
            # 模拟客户端初始化
            def mock_initialize():
                self.api.client = mock_client
            mock_init.side_effect = mock_initialize
            
            # 测试获取账户信息
            logger.info("测试: 模拟获取账户信息")
            result = await self.api.get_account_info()
            assert 'success' in result
            assert result['success'] == True
            assert 'account_info' in result
            assert result['account_info'] == mock_account_info
            logger.info("✓ 获取账户信息测试通过")
            
            # 测试获取持仓信息
            logger.info("测试: 模拟获取持仓信息")
            result = await self.api.get_open_positions()
            assert 'success' in result
            assert result['success'] == True
            assert 'positions' in result
            assert len(result['positions']) == 1
            position = result['positions'][0]
            assert position['symbol'] == "BTC"
            assert position['side'] == "long"
            logger.info("✓ 获取持仓信息测试通过")
            
            # 测试下单
            logger.info("测试: 模拟下单")
            order_result = await self.api.place_order(
                market_index=0,
                side='buy',
                quantity=0.0002,  # 对应约10 USD (基于50000 USD/BTC价格)
                price=None
            )
            assert order_result['success'] == True
            assert order_result['tx_hash'] == mock_tx_hash
            logger.info("✓ 下单测试通过")
            
            # 测试平仓
            logger.info("测试: 模拟平仓")
            close_result = await self.api.close_position(
                market_index=0,
                order_index=0
            )
            assert close_result['success'] == True
            assert close_result['tx_hash'] == mock_tx_hash
            logger.info("✓ 平仓测试通过")
            
            logger.info("所有模拟测试通过!")
            return True
    
    async def test_error_handling(self):
        """测试错误处理"""
        logger.info("测试: 错误处理")
        
        # 创建模拟客户端
        mock_client = AsyncMock()
        mock_client.api_client = Mock()
        mock_client.api_client.configuration = Mock()
        
        with patch.object(self.api, '_initialize_client') as mock_init, \
             patch('lighter.AccountApi') as mock_account_api_class:
            
            # 模拟客户端初始化
            def mock_initialize():
                self.api.client = mock_client
            mock_init.side_effect = mock_initialize
            
            # 模拟 API 错误
            mock_account_api_instance = AsyncMock()
            mock_account_api_class.return_value = mock_account_api_instance
            mock_account_api_instance.account.side_effect = Exception("模拟API错误")
            
            # 测试获取账户信息错误处理（非关键操作，应该返回结构化错误）
            result = await self.api.get_account_info()
            assert result['success'] == False, "非关键操作失败时应返回success=False"
            assert 'error' in result
            assert '模拟API错误' in result['error']
            logger.info("✓ 非关键操作错误处理测试通过")
            
            # 测试交易操作错误处理（关键操作，应该抛出异常）
            mock_client.create_market_order.side_effect = Exception("模拟交易错误")
            try:
                result = await self.api.place_order(
                    market_index=0,
                    side='buy',
                    quantity=0.0002,  # 对应约10 USD (基于50000 USD/BTC价格)
                    price=None
                )
                logger.error("✗ 关键操作错误处理测试失败 - 应该抛出异常")
                return False
            except Exception as e:
                assert "模拟交易错误" in str(e)
                logger.info("✓ 关键操作错误处理测试通过")
            
            return True

async def main():
    """主函数"""
    tester = MockLighterAPITester()
    
    try:
        # 运行模拟测试
        success = await tester.test_with_mocks()
        
        # 运行错误处理测试
        error_handling_success = await tester.test_error_handling()
        
        overall_success = success and error_handling_success
        
        if overall_success:
            logger.info("\n🎉 所有模拟测试通过!")
        else:
            logger.error("\n❌ 部分模拟测试失败")
        
        return overall_success
        
    except Exception as e:
        logger.error(f"模拟测试异常: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)