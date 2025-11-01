#!/usr/bin/env python3
"""
测试运行脚本
用于运行所有测试
"""

import subprocess
import sys
import os

def run_command(command, description):
    """运行命令并显示结果"""
    print(f"\n{'='*50}")
    print(f"运行: {description}")
    print(f"命令: {command}")
    print('='*50)
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ {description} 成功")
            if result.stdout:
                print(f"输出:\n{result.stdout}")
        else:
            print(f"✗ {description} 失败 (退出码: {result.returncode})")
            if result.stderr:
                print(f"错误:\n{result.stderr}")
            if result.stdout:
                print(f"输出:\n{result.stdout}")
        return result.returncode == 0
    except Exception as e:
        print(f"✗ {description} 异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始运行 Web3 Trading Bot 测试套件")
    
    # 检查是否在项目根目录
    if not os.path.exists('tests') or not os.path.exists('src'):
        print("错误: 请在项目根目录运行此脚本")
        return 1
    
    all_success = True
    
    # 1. 运行单元测试
    print("\n📋 运行单元测试...")
    success = run_command(
        "uv run python -m pytest tests/test_hedge_trading.py -v",
        "对冲交易单元测试"
    )
    all_success = all_success and success
    
    # 2. 运行模拟测试
    print("\n🎭 运行模拟测试...")
    success = run_command(
        "uv run python tests/test_lighter_api_mock.py",
        "LighterAPI 模拟测试"
    )
    all_success = all_success and success
    
    # 3. 检查测试配置
    print("\n⚙️  检查测试配置...")
    if os.path.exists('tests/test_config.yaml'):
        print("✓ 测试配置文件存在")
        
        # 4. 运行集成测试（如果配置存在）
        print("\n🔗 运行集成测试...")
        success = run_command(
            "uv run python tests/test_lighter_api_integration.py",
            "LighterAPI 集成测试"
        )
        all_success = all_success and success
    else:
        print("⚠️  测试配置文件不存在，跳过集成测试")
        print("   请运行: cp tests/test_config.yaml tests/test_config.yaml")
        print("   然后编辑 tests/test_config.yaml 配置测试账户")
    
    # 总结
    print(f"\n{'='*50}")
    if all_success:
        print("🎉 所有测试通过!")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())