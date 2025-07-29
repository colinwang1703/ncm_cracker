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
🚀 超级快速音频压缩器 (Ultra Fast Edition)
使用终极优化技术：
1. 更多并行进程 (最多8个)
2. FFmpeg最激进的速度优化
3. 内存缓冲优化
4. 智能格式检测
5. 独立compressed.txt记录
6. 实时性能监控
"""

import subprocess
import pathlib
import multiprocessing
import time
import threading
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, BarColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

console = Console()

# 全局锁用于文件写入
file_lock = threading.Lock()

def compress_audio_ultra_fast(input_file, output_file, bitrate='128k', sample_rate=44100):
    """超快速音频压缩函数 - 使用最激进的速度优化"""
    command = [
        'ffmpeg',
        '-y',  # 覆盖输出文件
        '-loglevel', 'error',  # 只显示错误信息
        '-i', str(input_file),
        '-c:a', 'libmp3lame',  # 使用LAME MP3编码器
        '-b:a', bitrate,
        '-ar', str(sample_rate),
        '-threads', '0',  # 使用所有可用线程
        '-preset', 'ultrafast',  # 最快编码预设
        '-q:a', '4',  # 快速质量设置
        '-compression_level', '1',  # 最低压缩级别 = 最快速度
        '-frame_size', '1152',  # 优化帧大小
        str(output_file)
    ]
    
    start_time = time.time()
    
    # 使用更优化的subprocess调用
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=8192  # 8KB缓冲区
    )
    
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, command, stderr)
    
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

def process_single_file_ultra(args):
    """单文件处理函数，用于多进程 - 超快速版本"""
    input_file, output_file, bitrate, sample_rate = args
    
    try:
        result = compress_audio_ultra_fast(input_file, output_file, bitrate, sample_rate)
        
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
            'error': f"FFmpeg错误: {e.stderr if hasattr(e, 'stderr') else str(e)}"
        }
    except Exception as e:
        return {
            'success': False,
            'input_file': input_file,
            'error': str(e)
        }

def detect_audio_files():
    """智能检测音频文件"""
    supported_formats = ['.flac', '.mp3', '.wav', '.m4a', '.aac', '.ogg', '.wma']
    audio_files = []
    
    for input_file in pathlib.Path('.').rglob('*.*'):
        if input_file.suffix.lower() in supported_formats:
            # 跳过result目录中的文件
            if 'result' in input_file.parts:
                continue
            # 跳过隐藏文件和系统文件
            if input_file.name.startswith('.'):
                continue
            audio_files.append(input_file)
    
    return audio_files

def main_compress_ultra():
    """主压缩函数 - 超快速版本"""
    console.print(Panel.fit("🚀 超级快速音频压缩器", style="bold red"))
    console.print("🔥 终极优化：最多8进程并行 + FFmpeg超快预设 + 内存优化")
    console.print("📁 使用规范化目录结构：02_decrypted -> 03_compressed")
    console.print("📝 使用独立的 compressed.txt 记录文件")
    console.print("💡 [bold yellow]WARNING: 追求极致速度，音质可能略有损失[/bold yellow]\n")
    
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
    
    # 查找需要压缩的文件（从02_decrypted目录）
    supported_formats = ['.flac', '.mp3', '.wav', '.m4a', '.aac', '.ogg']
    files_to_process = []
    
    for input_file in decrypted_dir.glob('*.*'):
        if input_file.suffix.lower() in supported_formats:
            if input_file.stem not in compressed:
                output_file = compressed_dir / f"{input_file.stem}.mp3"
                files_to_process.append((input_file, output_file, '128k', 44100))
    
    if not files_to_process:
        console.print("❌ 在 02_decrypted/ 目录中没有找到需要压缩的音频文件", style="red")
        console.print("💡 提示：请先解密NCM文件到 02_decrypted/ 目录", style="yellow")
        return
    
    total_size = sum(f[0].stat().st_size for f in files_to_process)
    # 超快速版本使用更多进程
    max_workers = min(multiprocessing.cpu_count(), len(files_to_process), 8)
    
    console.print(f"📁 找到 [bold cyan]{len(files_to_process)}[/bold cyan] 个文件需要压缩")
    console.print(f"💾 总大小: [bold yellow]{total_size/(1024*1024):.1f} MB[/bold yellow]")
    console.print(f"🚀 使用 [bold red]{max_workers}[/bold red] 个并行进程 (超快速模式)")
    console.print(f"📂 输出目录: [bold blue]03_compressed/[/bold blue]")
    console.print(f"🎯 支持格式: [bold blue]{', '.join(supported_formats)}[/bold blue]\n")
    
    # 创建结果统计表
    results_table = Table(title="🎵 超快速压缩结果统计")
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
        
        main_task = progress.add_task("🚀 超快速压缩中", total=len(files_to_process))
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(process_single_file_ultra, file_info): file_info[0].name 
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
                        
                        # 根据速度选择显示颜色
                        speed_style = "bold red" if stats['speed'] > 30 else "red" if stats['speed'] > 20 else "yellow"
                        
                        # 添加到结果表
                        results_table.add_row(
                            result['input_file'].name[:18] + "..." if len(result['input_file'].name) > 20 else result['input_file'].name,
                            f"{stats['input_size']/(1024*1024):.1f} MB",
                            f"{stats['output_size']/(1024*1024):.1f} MB",
                            f"{stats['compression_ratio']:.1f}%",
                            f"[{speed_style}]{stats['speed']:.1f} MB/s[/{speed_style}]",
                            "🚀 超快"
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
    
    summary_table.add_row("🎉 超快速压缩完成", "")
    summary_table.add_row("✅ 成功", f"[bold green]{successful}[/bold green] 个文件")
    summary_table.add_row("❌ 失败", f"[bold red]{failed}[/bold red] 个文件")
    summary_table.add_row("⏱️  总耗时", f"[bold yellow]{elapsed:.2f}[/bold yellow] 秒")
    summary_table.add_row("🚀 平均速度", f"[bold red]{avg_speed:.1f}[/bold red] MB/s")
    summary_table.add_row("💾 原始大小", f"[bold magenta]{total_input_size/(1024*1024):.1f}[/bold magenta] MB")
    summary_table.add_row("📦 压缩后大小", f"[bold blue]{total_output_size/(1024*1024):.1f}[/bold blue] MB")
    summary_table.add_row("📊 总压缩率", f"[bold red]{total_compression_ratio:.1f}%[/bold red]")
    
    # 添加节省空间和速度评价
    saved_space = total_input_size - total_output_size
    if saved_space > 0:
        summary_table.add_row("💰 节省空间", f"[bold green]{saved_space/(1024*1024):.1f}[/bold green] MB")
    
    if avg_speed > 50:
        summary_table.add_row("🔥 速度评价", "[bold red]疯狂压缩！[/bold red]")
    elif avg_speed > 30:
        summary_table.add_row("⚡ 速度评价", "[bold yellow]超快压缩！[/bold yellow]")
    else:
        summary_table.add_row("👍 速度评价", "[bold green]快速压缩！[/bold green]")
    
    console.print(Panel(summary_table, title="📊 超快速压缩统计", border_style="red"))

if __name__ == '__main__':
    main_compress_ultra()
