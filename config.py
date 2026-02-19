from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_KEY: str                        # مفتاح سري يشاركه Next.js فقط
    TEMP_DIR: str = "./tmp/audio_jobs"  # مجلد الملفات المؤقتة
    MAX_DURATION_SECONDS: int = 1800    # 30 دقيقة حد أقصى
    MAX_FILE_SIZE_MB: int = 200
    JOB_TTL_SECONDS: int = 3600         # حذف الوظيفة والملف بعد ساعة
    AUDIO_FORMAT: str = "mp3"
    AUDIO_QUALITY: str = "128k"
    AUDIO_CLIP_SECONDS: int = 30        # 0 = no limit

    model_config = {"env_file": ".env"}


settings = Settings()
