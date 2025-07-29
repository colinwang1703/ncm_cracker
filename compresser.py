import subprocess
import pathlib

def compress_audio(input_file, output_file, bitrate='128k', sample_rate=44100):
    command = [
        'ffmpeg',
        '-loglevel', 'error',  # 只显示错误信息
        '-i', str(input_file),
        '-b:a', bitrate,
        '-ar', str(sample_rate),
        str(output_file)
    ]
    subprocess.run(command, check=True)

# 读取已处理的文件列表
try:
    with open('cracked.txt', 'r', encoding='utf-8') as f:
        processed = set(f.read().strip().split('\n'))
except FileNotFoundError:
    processed = set()

# 创建 result 子目录
result_dir = pathlib.Path('result')
result_dir.mkdir(exist_ok=True)

# 处理所有需要压缩的音频文件
for input_file in pathlib.Path('.').rglob('*.*'):
    if input_file.suffix.lower() in ['.flac', '.mp3']:
        # 检查文件是否已经处理过
        file_name_without_ext = input_file.stem
        if file_name_without_ext in processed:
            print(f"跳过已处理的文件: {input_file.name}")
            continue
            
        output_file = result_dir / input_file.with_suffix('.mp3').name
        try:
            compress_audio(input_file, output_file)
            print(f"压缩完成: {input_file.name} -> {output_file.name}")
            
            # 将处理过的文件名添加到 cracked.txt
            with open('cracked.txt', 'a', encoding='utf-8') as f:
                f.write(file_name_without_ext + '\n')
        except subprocess.CalledProcessError as e:
            print(f"压缩失败: {input_file.name} - {e}")