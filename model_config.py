"""从项目的 .env 读取连接配置，不打印密钥。"""

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values
from langchain_openai import ChatOpenAI


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class ModelConfig:
    api_key: str = field(repr=False)
    base_url: str
    model: str


def load_config():
    # 固定从项目目录读取，避免从其他目录运行时找不到文件。
    values = dotenv_values(ROOT / ".env", encoding="utf-8-sig", interpolate=False)
    names = ("DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL", "DASHSCOPE_MODEL")
    missing = [name for name in names if not (values.get(name) or "").strip()]
    if missing:
        raise ValueError("请在 .env 中填写：" + "、".join(missing))
    key, url, model = ((values[name] or "").strip() for name in names)
    if not key.startswith("sk-") or any(c.isspace() for c in key):
        raise ValueError("API Key 格式不正确，请复制完整密钥，不要包含空格。")
    parsed = urlsplit(url)
    # 本项目只连接阿里云北京地域，防止把密钥发到误填的第三方地址。
    host = parsed.hostname or ""
    allowed = host.endswith(".cn-beijing.maas.aliyuncs.com") or host == "dashscope.aliyuncs.com"
    if (parsed.scheme != "https" or not allowed or parsed.username or parsed.password
            or parsed.port not in (None, 443) or parsed.query or parsed.fragment
            or parsed.path.rstrip("/") != "/compatible-mode/v1"):
        raise ValueError("Base URL 请填写北京地域的完整 OpenAI 兼容地址，末尾为 /compatible-mode/v1。")
    return ModelConfig(key, url.rstrip("/"), model)


def create_model(config):
    return ChatOpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model,
        use_responses_api=False,
        temperature=0,
        max_tokens=600,
        timeout=25,
        max_retries=0,
        # 千问 Chat Completions 扩展参数：关闭思考模式。
        extra_body={"enable_thinking": False},
    )


def friendly_error(error):
    """只输出受控提示，避免异常正文或请求头泄露密钥。"""
    status = getattr(error, "status_code", None)
    if status == 401:
        return "认证失败：检查密钥是否有效，以及密钥与接口地址是否属于同一地域。"
    if status == 403:
        return "调用被拒绝：检查模型权限、账户状态，以及免费额度用完即停开关。"
    if status == 404:
        return "未找到模型或接口：检查模型 ID 和 Base URL。"
    if status == 429:
        return "请求被限流或额度不足，请查看百炼控制台后稍后再试。"
    if status == 400:
        return "请求参数不被接受，请核对模型是否支持工具调用及当前配置。"
    if status and status >= 500:
        return "模型服务暂时不可用，请稍后再试。"
    if type(error).__name__ in ("APITimeoutError", "APIConnectionError"):
        return "连接失败或请求超时，请检查网络和接口地址。程序没有自动重试。"
    return "调用未完成，请检查配置、网络及依赖版本。程序没有自动重试。"
