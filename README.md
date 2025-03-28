# ComfyUI-GPT-API

[English](README_EN.md) | 中文

通过API直接调用GPT系列模型的ComfyUI扩展节点集合。该项目提供了一系列自定义节点（计划）

## 安装方法

1. 下载或克隆这个仓库到ComfyUI的`custom_nodes`目录中：
```
cd ComfyUI/custom_nodes
git clone https://github.com/CY-CHENYUE/ComfyUI-GPT-API
```

2. 安装依赖项：
```
cd ComfyUI-GPT-API
pip install -r requirements.txt
```

3. 重启ComfyUI，节点将自动加载

## 节点使用指南

### GPT4o Image Generation (图像生成节点)

#### 功能简介

通过API直接调用GPT-4o生成图像，可使用参考图像引导生成过程。

#### 使用方法

![alt text](workflow/ComfyUI-GPT-API.png)

1. 从节点浏览器中找到"GPT4o Image Generation"节点并添加到工作流中
2. 输入您的GPT API密钥、自定义API地址和模型名称（只需首次设置，将自动保存）
3. 编写的图像生成提示词
4. 连接一个参考图像到images输入（必需）
5. 运行工作流，节点将调用API生成图像并返回


## 注意事项

- 请确保您有有效的GPT API密钥
- API调用可能需要一定的时间，请耐心等待
- 图像生成受到API服务提供商的限制和规则约束
- 种子值设为0时系统会随机生成一个有效种子
- 所有配置（API密钥、URL、模型）将保存到节点目录，下次使用时自动加载

## 疑难解答

如果遇到安装或运行问题：

1. 确保已安装所有依赖项
2. 检查API密钥是否有效
3. 验证API URL是否正确
4. 确认使用的模型名称是服务商支持的
5. 检查网络连接是否正常
6. 查看节点返回的"API Respond"信息，获取详细错误信息

## Contact Me

- X (Twitter): [@cychenyue](https://x.com/cychenyue)
- TikTok: [@cychenyue](https://www.tiktok.com/@cychenyue)
- YouTube: [@CY-CHENYUE](https://www.youtube.com/@CY-CHENYUE)
- BiliBili: [@CY-CHENYUE](https://space.bilibili.com/402808950)
- 小红书: [@CY-CHENYUE](https://www.xiaohongshu.com/user/profile/6360e61f000000001f01bda0)