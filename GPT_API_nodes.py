import os
import base64
import io
import json
import torch
import numpy as np
from PIL import Image
import requests
from io import BytesIO
import traceback
import random
import time

class GPTImageGenerator:
    @classmethod
    def INPUT_TYPES(cls):
        # 创建临时实例以加载配置
        temp_instance = cls()
        config = temp_instance.load_config()
        
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True}),
                "api_key": ("STRING", {"default": "", "multiline": False}),
                "model": ("STRING", {"default": config["model"], "multiline": False}),
                "api_url": ("STRING", {"default": config["api_url"], "multiline": False}),
                "images": ("IMAGE",),
                "seed": ("INT", {"default": 66666666, "min": 0, "max": 4294967295}),
            },
            "optional": {
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "API Respond")
    FUNCTION = "generate_image"
    CATEGORY = "GPT-API"
    
    def __init__(self):
        """初始化日志系统和API密钥存储"""
        self.log_messages = []  # 全局日志消息存储
        # 获取节点所在目录
        self.node_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(self.node_dir, "gpt_api_config.json")
    
    def log(self, message):
        """全局日志函数：记录到日志列表"""
        if hasattr(self, 'log_messages'):
            self.log_messages.append(message)
        return message
    
    def save_config(self, api_key, api_url, model):
        """保存API配置到文件"""
        if not api_key or len(api_key) < 10:
            return False
            
        try:
            config = {
                "api_key": api_key,
                "api_url": api_url,
                "model": model,
                "saved_time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.config_file, "w") as f:
                json.dump(config, f)
            self.log("已保存API配置到节点目录")
            return True
        except Exception as e:
            self.log(f"保存API配置失败: {e}")
            return False
    
    def load_config(self):
        """从文件加载API配置"""
        default_config = {
            "api_key": "",
            "api_url": "API URL",
            "model": "MODEL NAME"
        }
        
        if not os.path.exists(self.config_file):
            return default_config
            
        try:
            with open(self.config_file, "r") as f:
                config = json.load(f)
                
            # 验证必要字段
            if "api_key" not in config or len(config["api_key"]) < 10:
                self.log("已保存的API密钥无效")
                return default_config
                
            self.log("成功加载已保存的API配置")
            return config
        except Exception as e:
            self.log(f"加载API配置失败: {e}")
            return default_config
    
    def get_api_key(self, user_input_key, user_api_url, user_model):
        """获取API密钥和配置，优先使用用户输入的值"""
        # 如果用户输入了有效的密钥，使用并保存所有配置
        if user_input_key and len(user_input_key) > 10:
            self.log("使用用户输入的API配置")
            # 保存到文件中
            self.save_config(user_input_key, user_api_url, user_model)
            return user_input_key
            
        # 如果用户没有输入，尝试从文件读取
        config = self.load_config()
        if config["api_key"] and len(config["api_key"]) > 10:
            self.log("使用已保存的API配置")
            return config["api_key"]
                
        # 如果都没有，返回空字符串
        self.log("警告: 未提供有效的API密钥")
        return ""
        
    def get_saved_api_url(self):
        """获取保存的API URL"""
        config = self.load_config()
        return config["api_url"]
        
    def get_saved_model(self):
        """获取保存的模型名称"""
        config = self.load_config()
        return config["model"]
    
    def generate_empty_image(self, width=512, height=512):
        """生成标准格式的空白RGB图像张量"""
        empty_image = np.ones((height, width, 3), dtype=np.float32) * 0.2
        tensor = torch.from_numpy(empty_image).unsqueeze(0) # [1, H, W, 3]
        
        self.log(f"创建ComfyUI兼容的空白图像: 形状={tensor.shape}, 类型={tensor.dtype}")
        return tensor
    
    def encode_images_to_base64(self, image_tensor):
        """将ComfyUI的图像张量(单张或多张)转换为base64编码的列表"""
        try:
            # 确定图像数量
            batch_size = image_tensor.shape[0]
            self.log(f"检测到 {batch_size} 张参考图像")
            
            base64_images = []
            
            # 逐一处理每张图像
            for i in range(batch_size):
                # 获取单张图像
                input_image = image_tensor[i].cpu().numpy()
                
                # 转换为PIL图像
                input_image = (input_image * 255).astype(np.uint8)
                pil_image = Image.fromarray(input_image)
                
                self.log(f"参考图像 {i+1} 处理成功，尺寸: {pil_image.width}x{pil_image.height}")
                
                # 转换为base64
                buffered = BytesIO()
                pil_image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                base64_images.append(img_str)
            
            return base64_images
        except Exception as e:
            self.log(f"图像转base64编码失败: {str(e)}")
            return None
    
    def generate_image(self, prompt, api_key, model, api_url, images, seed):
        """生成图像 - 支持参考图片(单张或多张)，可设置随机种子"""
        response_text = ""
        
        # 重置日志消息
        self.log_messages = []
        
        try:
            # 直接使用节点传入的种子值，ComfyUI已经处理了随机种子生成
            self.log(f"使用种子值: {seed}")
            
            # 设置随机种子，确保潜在的随机行为是可重现的
            torch.manual_seed(seed)
            np.random.seed(seed)
            random.seed(seed)
            
            # 获取API密钥和配置
            config = self.load_config()
            
            # 如果用户提供了API密钥，保存整个配置
            if api_key and len(api_key) > 10:
                self.save_config(api_key, api_url, model)
                actual_api_key = api_key
                actual_api_url = api_url
                actual_model = model
            else:
                # 否则使用已保存的配置
                actual_api_key = config["api_key"]
                actual_api_url = api_url or config["api_url"]
                actual_model = model or config["model"]
                
                # 记录使用的配置
                if actual_api_key:
                    self.log("使用已保存的API配置")
                
            if not actual_api_key:
                error_message = "错误: 未提供有效的API密钥。请在节点中输入API密钥或确保已保存密钥。"
                self.log(error_message)
                full_text = "## 错误\n" + error_message + "\n\n## 使用说明\n1. 在节点中输入您的GPT API密钥\n2. 密钥将自动保存到节点目录，下次可以不必输入"
                return (self.generate_empty_image(512, 512), full_text) # 返回空白图像
            
            # 准备请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {actual_api_key}"
            }
            
            # 构建请求内容
            content_items = []
            
            # 添加提示文本（在用户提示词前加上指示生成图片的引导语）
            image_generation_prompt = "Generate an image based on this description. Please provide the image directly as a URL or base64 data. Do not add explanations in your response, just return the image. Description:\n\n" + prompt
            content_items.append({
                "type": "text",
                "text": image_generation_prompt
            })
            
            # 添加图像（现在是必需的，可以是多张）
            base64_images = self.encode_images_to_base64(images)
            if not base64_images or len(base64_images) == 0:
                error_message = "错误: 无法编码输入图像。请检查图像是否有效。"
                self.log(error_message)
                return (self.generate_empty_image(512, 512), error_message)  # 返回空白图像
            
            # 添加所有图像到请求中
            for i, img_base64 in enumerate(base64_images):
                self.log(f"将图像 {i+1} 添加到请求中")
                content_items.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_base64}"
                    }
                })
            
            self.log(f"成功添加 {len(base64_images)} 张图像到请求中")
            
            # 准备请求数据 - 使用chat completions格式
            payload = {
                "model": actual_model,
                "messages": [
                    {
                        "role": "user",
                        "content": content_items
                    }
                ],
                "seed": seed  # 在API请求中添加种子参数
            }
            
            # 记录请求信息
            self.log(f"请求GPT API，模型: {actual_model}，包含 {len(base64_images)} 张图像，种子: {seed}")
            
            # 发送API请求
            self.log(f"发送API请求到: {actual_api_url}")
            
            response = requests.post(actual_api_url, headers=headers, json=payload)
            
            # 记录API响应
            status_code = response.status_code
            self.log(f"API响应状态码: {status_code}")
            
            if status_code != 200:
                error_msg = f"API请求失败，状态码: {status_code}，响应: {response.text}"
                self.log(error_msg)
                return (self.generate_empty_image(512, 512), error_msg)  # 返回空白图像
            
            # 解析响应
            response_json = response.json()
            
            # 保存响应文本用于返回
            response_text = json.dumps(response_json, ensure_ascii=False, indent=2)
            self.log("API响应接收成功，正在处理...")
            
            # 提取响应内容
            try:
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    message = response_json["choices"][0]["message"]
                    if "content" in message:
                        # 获取GPT回复的文本内容
                        text_content = message["content"]
                        self.log(f"提取到GPT响应文本: {text_content[:100]}..." if len(text_content) > 100 else text_content)
                        
                        # 检查是否包含base64图像数据
                        image_data_match = None
                        
                        # 尝试查找文本中可能包含的图像URL
                        import re
                        # 查找可能的图像URL
                        url_pattern = r'https?://[^\s<>"]+\.(?:jpg|jpeg|png|gif|webp)'
                        urls = re.findall(url_pattern, text_content)
                        
                        # 查找可能的base64图像数据
                        base64_pattern = r'data:image\/[^;]+;base64,([a-zA-Z0-9+/=]+)'
                        base64_matches = re.findall(base64_pattern, text_content)
                        
                        if urls:
                            # 如果找到URL，尝试下载第一个图像
                            self.log(f"在响应中发现图像URL: {urls[0]}")
                            try:
                                img_response = requests.get(urls[0])
                                if img_response.status_code == 200:
                                    # 从URL加载图像
                                    buffer = BytesIO(img_response.content)
                                    pil_image = Image.open(buffer)
                                    
                                    # 确保是RGB模式
                                    if pil_image.mode != 'RGB':
                                        pil_image = pil_image.convert('RGB')
                                    
                                    self.log(f"成功从URL加载图像: {pil_image.width}x{pil_image.height}")
                                    
                                    # 转换为ComfyUI格式
                                    img_array = np.array(pil_image).astype(np.float32) / 255.0
                                    img_tensor = torch.from_numpy(img_array).unsqueeze(0)
                                    
                                    # 构建返回文本
                                    result_text = f"## GPT响应\n\n{text_content}\n\n"
                                    result_text += f"\n## 处理信息\n已从URL加载图像: {urls[0]}"
                                    result_text += f"\n种子: {seed}"
                                    result_text += f"\n\n## 处理日志\n" + "\n".join(self.log_messages)
                                    
                                    return (img_tensor, result_text)
                            except Exception as e:
                                self.log(f"从URL加载图像失败: {e}")
                        
                        elif base64_matches:
                            # 如果找到base64数据，尝试解码
                            self.log("在响应中发现base64编码的图像数据")
                            try:
                                img_data = base64.b64decode(base64_matches[0])
                                buffer = BytesIO(img_data)
                                pil_image = Image.open(buffer)
                                
                                # 确保是RGB模式
                                if pil_image.mode != 'RGB':
                                    pil_image = pil_image.convert('RGB')
                                
                                self.log(f"成功从base64加载图像: {pil_image.width}x{pil_image.height}")
                                
                                # 转换为ComfyUI格式
                                img_array = np.array(pil_image).astype(np.float32) / 255.0
                                img_tensor = torch.from_numpy(img_array).unsqueeze(0)
                                
                                # 构建返回文本
                                result_text = f"## GPT响应\n\n{text_content}\n\n"
                                result_text += f"\n## 处理信息\n已从base64数据加载图像"
                                result_text += f"\n种子: {seed}"
                                result_text += f"\n\n## 处理日志\n" + "\n".join(self.log_messages)
                                
                                return (img_tensor, result_text)
                            except Exception as e:
                                self.log(f"从base64数据加载图像失败: {e}")
                        
                        # 如果没有找到图像，返回空白图像
                        self.log("在响应中未找到图像数据，返回空白图像")
                        
                        # 创建空白图像
                        empty_img = self.generate_empty_image(512, 512)
                        
                        # 构建返回文本
                        result_text = f"## GPT响应\n\n{text_content}\n\n"
                        result_text += f"\n## 请求信息\n模型: {actual_model}\n提示词: {prompt}\n种子: {seed}"
                        result_text += f"\n\n## 处理日志\n" + "\n".join(self.log_messages)
                        
                        return (empty_img, result_text)
            
            except Exception as e:
                error_message = f"处理API响应时出错: {str(e)}"
                self.log(error_message)
                traceback.print_exc()
            
            # 如果无法提取有效内容，返回原始响应
            self.log("无法从响应中提取有效的图像或文本内容")
            full_text = f"## API响应\n" + response_text + f"\n\n## 种子\n{seed}\n\n## 处理日志\n" + "\n".join(self.log_messages)
            return (self.generate_empty_image(512, 512), full_text)  # 返回空白图像
        
        except Exception as e:
            error_message = f"处理过程中出错: {str(e)}"
            self.log(f"GPT API调用错误: {str(e)}")
            traceback.print_exc()
            
            # 合并日志和错误信息
            full_text = f"## 错误\n" + error_message + f"\n\n## 种子\n{seed}\n\n## 处理日志\n" + "\n".join(self.log_messages)
            return (self.generate_empty_image(512, 512), full_text)  # 返回空白图像

# 注册节点
NODE_CLASS_MAPPINGS = {
    "GPT-ImageGenerator": GPTImageGenerator
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GPT-ImageGenerator": "GPT4o Image Generation"
} 