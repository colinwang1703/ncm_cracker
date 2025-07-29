# This file is part of ncm_cracker.
#
# ncm_cracker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ncm_cracker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ncm_cracker.  If not, see <https://www.gnu.org/licenses/>.
"""
🚀 超快速音频压缩器
使用多种优化技术：
1. 多进程并行压缩
2. FFmpeg优化参数
3. 智能跳过已处理文件
4. Rich进度条显示
5. 独立的compressed.txt记录文件
"""

import subprocess
import pathlib
import multiprocessing
import time
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, BarColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

console = Console()

# 全局锁用于文件写入
file_lock = threading.Lock()

def compress_audio_optimized(input_file, output_file, bitrate='128k', sample_rate=44100):
    """优化的音频压缩函数"""
    command = [
        'ffmpeg',
        '-y',  # 覆盖输出文件
        '-loglevel', 'error',  # 只显示错误信息
        '-i', str(input_file),
        '-c:a', 'libmp3lame',  # 使用LAME MP3编码器
        '-b:a', bitrate,
        '-ar', str(sample_rate),
        '-threads', '0',  # 使用所有可用线程
        '-preset', 'fast',  # 快速编码预设
        str(output_file)
    ]
    
    start_time = time.time()
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    elapsed = time.time() - start_time
    
    # 获取文件大小信息
    input_size = input_file.stat().st_size
    output_size = output_file.stat().st_size
    compression_ratio = (1 - output_size / input_size) * 100 if input_size > 0 else 0
    
    return {
        'input_size': input_size,
        'output_size': output_size,
        'compression_ratio': compression_ratio,
        'processing_time': elapsed,
        'speed': input_size / (1024 * 1024) / elapsed if elapsed > 0 else 0
    }

def process_single_file(args):
    """单文件处理函数，用于多进程"""
    input_file, output_file, bitrate, sample_rate = args
    
    try:
        result = compress_audio_optimized(input_file, output_file, bitrate, sample_rate)
        
        # 线程安全地写入已处理文件列表
        with file_lock:
            with open('compressed.txt', 'a', encoding='utf-8') as f:
                f.write(input_file.stem + '\n')
        
        return {
            'success': True,
            'input_file': input_file,
            'output_file': output_file,
            'stats': result
        }
    except subprocess.CalledProcessError as e:
        return {
            'success': False,
            'input_file': input_file,
            'error': str(e)
        }
    except Exception as e:
        return {
            'success': False,
            'input_file': input_file,
            'error': str(e)
        }

def main_compress():
    """主压缩函数"""
    console.print(Panel.fit("🎵 超快速音频压缩器", style="bold magenta"))
    console.print("✨ 优化技术：多进程并行 + FFmpeg优化 + 智能跳过")
    console.print("📁 使用规范化目录结构：02_decrypted -> 03_compressed")
    console.print("📝 使用独立的 compressed.txt 记录文件\n")
    
    # 确保目录结构存在
    decrypted_dir = pathlib.Path("02_decrypted")  
    compressed_dir = pathlib.Path("03_compressed")
    decrypted_dir.mkdir(exist_ok=True)
    compressed_dir.mkdir(exist_ok=True)
    
    # 读取已压缩的文件列表
    try:
        with open('compressed.txt', 'r', encoding='utf-8') as f:
            compressed = set(f.read().strip().split('\n'))
    except FileNotFoundError:
        compressed = set()
    
    # 创建输出目录
    result_dir = pathlib.Path('result')
    result_dir.mkdir(exist_ok=True)
    
    # 查找需要压缩的文件（从02_decrypted目录）
    files_to_process = []
    supported_formats = ['.flac', '.mp3', '.wav', '.m4a', '.aac']
    
    for input_file in decrypted_dir.glob('*.*'):
        if input_file.suffix.lower() in supported_formats:
            file_name_without_ext = input_file.stem
            if file_name_without_ext not in compressed:
                output_file = compressed_dir / f"{input_file.stem}.mp3"
                files_to_process.append((input_file, output_file, '128k', 44100))
    
    if not files_to_process:
        console.print("❌ 在 02_decrypted/ 目录中没有找到需要压缩的音频文件", style="red")
        console.print("💡 提示：请先解密NCM文件到 02_decrypted/ 目录", style="yellow")
        return
    
    total_size = sum(f[0].stat().st_size for f in files_to_process)
    max_workers = min(multiprocessing.cpu_count(), len(files_to_process), 4)
    
    console.print(f"📁 找到 [bold cyan]{len(files_to_process)}[/bold cyan] 个文件需要压缩")
    console.print(f"💾 总大小: [bold yellow]{total_size/(1024*1024):.1f} MB[/bold yellow]")
    console.print(f"⚡ 使用 [bold green]{max_workers}[/bold green] 个并行进程")
    console.print(f"📂 输出目录: [bold blue]03_compressed/[/bold blue]")
    console.print(f"🎯 支持格式: [bold blue]{', '.join(supported_formats)}[/bold blue]\n")
    
    # 创建结果统计表
    results_table = Table(title="🎵 压缩结果统计")
    results_table.add_column("文件名", style="cyan", width=20)
    results_table.add_column("原大小", justify="right", style="yellow")
    results_table.add_column("压缩后", justify="right", style="green")
    results_table.add_column("压缩率", justify="right", style="blue")
    results_table.add_column("速度", justify="right", style="red")
    results_table.add_column("状态", justify="center")
    
    # 并行处理文件
    successful = 0
    failed = 0
    total_input_size = 0
    total_output_size = 0
    start_time = time.time()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False
    ) as progress:
        
        main_task = progress.add_task("🎵 压缩进度", total=len(files_to_process))
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(process_single_file, file_info): file_info[0].name 
                for file_info in files_to_process
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                file_name = future_to_file[future]
                try:
                    result = future.result()
                    if result['success']:
                        successful += 1
                        stats = result['stats']
                        total_input_size += stats['input_size']
                        total_output_size += stats['output_size']
                        
                        # 添加到结果表
                        results_table.add_row(
                            result['input_file'].name[:18] + "..." if len(result['input_file'].name) > 20 else result['input_file'].name,
                            f"{stats['input_size']/(1024*1024):.1f} MB",
                            f"{stats['output_size']/(1024*1024):.1f} MB",
                            f"{stats['compression_ratio']:.1f}%",
                            f"{stats['speed']:.1f} MB/s",
                            "✅ 成功"
                        )
                    else:
                        failed += 1
                        results_table.add_row(
                            result['input_file'].name[:18] + "..." if len(result['input_file'].name) > 20 else result['input_file'].name,
                            "N/A",
                            "N/A",
                            "N/A",
                            "N/A",
                            "❌ 失败"
                        )
                except Exception as e:
                    failed += 1
                    results_table.add_row(
                        file_name[:18] + "..." if len(file_name) > 20 else file_name,
                        "N/A",
                        "N/A",
                        "N/A",
                        "N/A",
                        "💥 异常"
                    )
                
                progress.advance(main_task)
    
    elapsed = time.time() - start_time
    avg_speed = total_input_size / (1024 * 1024) / elapsed if elapsed > 0 else 0
    total_compression_ratio = (1 - total_output_size / total_input_size) * 100 if total_input_size > 0 else 0
    
    # 显示结果表
    console.print("\n")
    console.print(results_table)
    
    # 显示总结信息
    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("", style="bold")
    summary_table.add_column("", style="")
    
    summary_table.add_row("🎉 压缩完成", "")
    summary_table.add_row("✅ 成功", f"[bold green]{successful}[/bold green] 个文件")
    summary_table.add_row("❌ 失败", f"[bold red]{failed}[/bold red] 个文件")
    summary_table.add_row("⏱️  总耗时", f"[bold yellow]{elapsed:.2f}[/bold yellow] 秒")
    summary_table.add_row("🚀 平均速度", f"[bold cyan]{avg_speed:.1f}[/bold cyan] MB/s")
    summary_table.add_row("💾 原始大小", f"[bold magenta]{total_input_size/(1024*1024):.1f}[/bold magenta] MB")
    summary_table.add_row("📦 压缩后大小", f"[bold blue]{total_output_size/(1024*1024):.1f}[/bold blue] MB")
    summary_table.add_row("📊 总压缩率", f"[bold red]{total_compression_ratio:.1f}%[/bold red]")
    
    # 添加节省空间提示
    saved_space = total_input_size - total_output_size
    if saved_space > 0:
        summary_table.add_row("💰 节省空间", f"[bold green]{saved_space/(1024*1024):.1f}[/bold green] MB")
    
    console.print(Panel(summary_table, title="📊 压缩统计", border_style="magenta"))

if __name__ == '__main__':
    main_compress()