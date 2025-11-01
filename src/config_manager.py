import yaml
import os

def load_config(config_path='config.yaml'):
    """
    加载配置文件
    
    Args:
        config_path (str): 配置文件路径
        
    Returns:
        dict: 配置信息字典
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件 {config_path} 不存在")
    
    with open(config_path, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    
    # 验证必要配置项
    required_keys = ['trading_pair', 'leverage', 'position_size', 'stop_loss_threshold', 'proxy_pool', 'api_credentials']
    for key in required_keys:
        if key not in config:
            raise ValueError(f"配置文件缺少必要的配置项: {key}")
    
    # 验证代理池配置
    if not config['proxy_pool']:
        raise ValueError("代理池配置不能为空")
    
    # 验证代理池中的每个代理配置
    for i, proxy in enumerate(config['proxy_pool']):
        required_proxy_keys = ['name', 'host', 'port']
        for key in required_proxy_keys:
            if key not in proxy:
                raise ValueError(f"第{i+1}个代理配置缺少必要的配置项: {key}")
        
        # 如果提供了认证信息，必须同时提供用户名和密码
        if 'username' in proxy and 'password' not in proxy:
            raise ValueError(f"第{i+1}个代理配置提供了用户名但缺少密码")
        if 'password' in proxy and 'username' not in proxy:
            raise ValueError(f"第{i+1}个代理配置提供了密码但缺少用户名")
    
    # 验证API凭证数量
    if len(config['api_credentials']) < 2:
        raise ValueError("至少需要提供2个API凭证")
    
    # 验证每个API凭证是否包含必要的字段
    for i, credential in enumerate(config['api_credentials']):
        required_credential_keys = ['account_name', 'api_key', 'account_index', 'api_key_index', 'network']
        for key in required_credential_keys:
            if key not in credential:
                raise ValueError(f"第{i+1}个API凭证缺少必要的配置项: {key}")
        
        # 验证网络类型
        if credential['network'] not in ['mainnet', 'testnet']:
            raise ValueError(f"第{i+1}个API凭证的网络类型不支持: {credential['network']}，仅支持 'mainnet' 或 'testnet'")
    
    return config