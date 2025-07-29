"""
🚀 超快速 NCM 解密器
使用多种黑科技优化技术：
1. NumPy 向量化操作 - 把Python循环变成C级别运算
2. 预计算查找表 - 避免重复计算  
3. 内存映射文件 - 直接操作内存，避免频繁I/O
4. 多进程并行 - 榨干CPU每个核心
5. 大缓冲区处理 - 1MB vs 32KB，减少系统调用
"""

import numpy as np
import mmap
import multiprocessing
import pathlib
from concurrent.futures import ProcessPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, BarColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
import binascii
import struct
import base64
import json
import os
import threading
from Crypto.Cipher import AES
import time

console = Console()

# 全局锁
file_lock = threading.Lock()

def create_key_lookup_table(key_box):
    """预计算密钥查找表以加速解密 - 这是速度提升的关键！"""
    lookup_table = np.zeros(256, dtype=np.uint8)
    for j in range(256):
        lookup_table[j] = key_box[(key_box[j] + key_box[(key_box[j] + j) & 0xff]) & 0xff]
    return lookup_table

def decrypt_chunk_vectorized(chunk_data, key_lookup, start_offset):
    """使用 NumPy 向量化操作进行超快速解密 - 核心黑科技！"""
    chunk_array = np.frombuffer(chunk_data, dtype=np.uint8)
    indices = np.arange(1, len(chunk_data) + 1, dtype=np.uint32)
    indices = (start_offset + indices) & 0xff
    
    # 向量化异或操作 - 这里是速度暴增的秘密！
    decrypted = chunk_array ^ key_lookup[indices]
    return decrypted.tobytes()

def dump_ultra_fast(file_path, name):
    """超快速解密函数"""
    core_key = binascii.a2b_hex("687A4852416D736F356B496E62617857")
    meta_key = binascii.a2b_hex("2331346C6A6B5F215C5D2630553C2728")
    unpad = lambda s: s[0:-(s[-1] if type(s[-1]) == int else ord(s[-1]))]
    
    try:
        file_size = os.path.getsize(file_path)
        
        with open(file_path, 'rb') as f:
            # 使用内存映射加速文件读取
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                # 验证文件头
                if mmapped_file[:8] != b'CTENFDAM':
                    raise ValueError("Invalid NCM file format")
                
                offset = 10  # 跳过文件头和2字节间隔
                
                # 读取并解密密钥
                key_length = struct.unpack('<I', mmapped_file[offset:offset+4])[0]
                offset += 4
                
                key_data = bytearray(mmapped_file[offset:offset+key_length])
                offset += key_length
                
                # 优化的异或操作
                key_data = np.frombuffer(key_data, dtype=np.uint8) ^ 0x64
                
                cryptor = AES.new(core_key, AES.MODE_ECB)
                key_data = unpad(cryptor.decrypt(key_data.tobytes()))[17:]
                
                # 生成密钥盒（这部分无法避免循环）
                key_box = bytearray(range(256))
                c = 0
                last_byte = 0
                key_offset = 0
                key_length = len(key_data)
                
                for i in range(256):
                    swap = key_box[i]
                    c = (swap + last_byte + key_data[key_offset]) & 0xff
                    key_offset = (key_offset + 1) % key_length
                    key_box[i] = key_box[c]
                    key_box[c] = swap
                    last_byte = c
                
                # 预计算查找表
                key_lookup = create_key_lookup_table(key_box)
                
                # 读取元数据
                meta_length = struct.unpack('<I', mmapped_file[offset:offset+4])[0]
                offset += 4
                
                meta_data = np.frombuffer(
                    mmapped_file[offset:offset+meta_length], 
                    dtype=np.uint8
                ) ^ 0x63
                offset += meta_length
                
                meta_data = base64.b64decode(meta_data.tobytes()[22:])
                cryptor = AES.new(meta_key, AES.MODE_ECB)
                meta_data = json.loads(unpad(cryptor.decrypt(meta_data)).decode('utf-8')[6:])
                
                # 跳过CRC32和封面数据
                offset += 4  # CRC32
                offset += 5  # gap
                image_size = struct.unpack('<I', mmapped_file[offset:offset+4])[0]
                offset += 4 + image_size
                
                # 准备输出文件
                file_name = os.path.splitext(os.path.basename(file_path))[0] + '.' + meta_data['format']
                output_path = os.path.join("02_decrypted", file_name)
                
                # 音频数据处理 - 使用1MB大缓冲区！
                audio_data_size = file_size - offset
                CHUNK_SIZE = 1024 * 1024  # 1MB 块大小 - 比普通版本大4倍！
                
                start_time = time.time()
                
                with open(output_path, 'wb') as output_file:
                    processed = 0
                    
                    while processed < audio_data_size:
                        chunk_size = min(CHUNK_SIZE, audio_data_size - processed)
                        chunk_data = mmapped_file[offset + processed:offset + processed + chunk_size]
                        
                        # 使用向量化解密 - 这里是魔法发生的地方！
                        decrypted_chunk = decrypt_chunk_vectorized(chunk_data, key_lookup, processed)
                        output_file.write(decrypted_chunk)
                        processed += chunk_size
                
                elapsed = time.time() - start_time
                speed = audio_data_size / (1024 * 1024) / elapsed if elapsed > 0 else 0
        
        # 线程安全地写入已处理文件列表
        with file_lock:
            with open('cracked.txt', 'a', encoding='utf-8') as f:
                f.write(name + '\n')
        
        return file_name, speed, audio_data_size
        
    except Exception as e:
        return None, 0, 0

def process_file_ultra_fast(args):
    """多进程包装函数"""
    file_path, name = args
    return dump_ultra_fast(file_path, name)

def main_ultra_fast():
    """主函数，实现超快速并行处理"""
    console.print(Panel.fit("🚀 NCM 超快速解密器", style="bold magenta"))
    console.print("💫 黑科技加持：NumPy向量化 + 内存映射 + 预计算查找表 + 多进程并行")
    console.print("📁 使用规范化目录结构：01_original -> 02_decrypted")
    console.print("⚡ [bold yellow]速度暴增的秘密武器全开启！[/bold yellow]\n")
    
    # 确保目录结构存在
    original_dir = pathlib.Path("01_original")
    decrypted_dir = pathlib.Path("02_decrypted")
    original_dir.mkdir(exist_ok=True)
    decrypted_dir.mkdir(exist_ok=True)
    
    try:
        with open('cracked.txt', 'r', encoding='utf-8') as f:
            cracked = set(f.read().strip().split('\n'))
    except FileNotFoundError:
        cracked = set()
    
    # 查找需要处理的文件（从01_original目录）
    files_to_process = []
    
    for file in original_dir.glob("*.ncm"):
        name = file.stem
        if name not in cracked:
            files_to_process.append((str(file), name))
    
    if not files_to_process:
        console.print("❌ 在 01_original/ 目录中没有找到需要处理的 .ncm 文件", style="red")
        console.print("💡 提示：请将NCM文件放入 01_original/ 目录", style="yellow")
        return
    
    total_size = sum(pathlib.Path(fp).stat().st_size for fp, _ in files_to_process)
    max_workers = min(multiprocessing.cpu_count(), len(files_to_process), 6)
    
    console.print(f"📁 找到 [bold cyan]{len(files_to_process)}[/bold cyan] 个文件需要处理")
    console.print(f"💾 总大小: [bold yellow]{total_size/(1024*1024):.1f} MB[/bold yellow]")
    console.print(f"🔥 使用 [bold red]{max_workers}[/bold red] 个并行进程 (超快速模式)")
    console.print(f"📂 输出目录: [bold blue]02_decrypted/[/bold blue]")
    console.print("🎯 [bold green]准备释放洪荒之力...[/bold green]\n")
    console.print(f"🔥 使用 [bold red]{max_workers}[/bold red] 个并行进程 (超快速模式)")
    console.print("🎯 [bold green]准备释放洪荒之力...[/bold green]\n")
    
    # 创建结果统计表
    results_table = Table(title="🎵 超快速解密结果统计")
    results_table.add_column("文件名", style="cyan", width=25)
    results_table.add_column("大小", justify="right", style="yellow")
    results_table.add_column("速度", justify="right", style="red")
    results_table.add_column("状态", justify="center")
    
    # 并行处理文件
    successful = 0
    failed = 0
    total_processed_size = 0
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
        
        main_task = progress.add_task("🚀 超快速处理中", total=len(files_to_process))
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(process_file_ultra_fast, file_info): file_info 
                for file_info in files_to_process
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                file_path, file_name = future_to_file[future]
                try:
                    result = future.result()
                    if result and len(result) == 3:
                        output_name, speed, file_size = result
                        successful += 1
                        total_processed_size += file_size
                        
                        # 添加到结果表 - 用红色显示超高速度！
                        speed_style = "bold red" if speed > 50 else "green"
                        results_table.add_row(
                            file_name[:23] + "..." if len(file_name) > 25 else file_name,
                            f"{file_size/(1024*1024):.1f} MB",
                            f"[{speed_style}]{speed:.1f} MB/s[/{speed_style}]",
                            "🚀 超快"
                        )
                    else:
                        failed += 1
                        results_table.add_row(
                            file_name[:23] + "..." if len(file_name) > 25 else file_name,
                            "N/A",
                            "N/A",
                            "❌ 失败"
                        )
                except Exception as e:
                    failed += 1
                    results_table.add_row(
                        file_name[:23] + "..." if len(file_name) > 25 else file_name,
                        "N/A",
                        "N/A",
                        "💥 异常"
                    )
                
                progress.advance(main_task)
    
    elapsed = time.time() - start_time
    avg_speed = total_processed_size / (1024 * 1024) / elapsed if elapsed > 0 else 0
    
    # 显示结果表
    console.print("\n")
    console.print(results_table)
    
    # 显示总结信息 - 特别强调超高速度
    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("", style="bold")
    summary_table.add_column("", style="")
    
    summary_table.add_row("🎉 超快速处理完成", "")
    summary_table.add_row("✅ 成功", f"[bold green]{successful}[/bold green] 个文件")
    summary_table.add_row("❌ 失败", f"[bold red]{failed}[/bold red] 个文件")
    summary_table.add_row("⏱️  总耗时", f"[bold yellow]{elapsed:.2f}[/bold yellow] 秒")
    summary_table.add_row("🚀 平均速度", f"[bold red]{avg_speed:.1f}[/bold red] MB/s")
    summary_table.add_row("💾 总处理量", f"[bold magenta]{total_processed_size/(1024*1024):.1f}[/bold magenta] MB")
    
    # 添加速度对比提示
    if avg_speed > 100:
        summary_table.add_row("🔥 速度评价", "[bold red]疯狂加速！[/bold red]")
    elif avg_speed > 50:
        summary_table.add_row("⚡ 速度评价", "[bold yellow]超快模式！[/bold yellow]")
    else:
        summary_table.add_row("👍 速度评价", "[bold green]优秀速度！[/bold green]")
    
    console.print(Panel(summary_table, title="📊 超快速性能统计", border_style="red"))

if __name__ == '__main__':
    # 检查是否安装了 numpy
    try:
        import numpy as np
        main_ultra_fast()
    except ImportError:
        print("错误: 需要安装 numpy 才能使用超快速模式")
        print("请运行: pip install numpy")
        
        # 回退到普通优化版本
        print("\n回退到普通优化版本...")
        from crack import main
        main()
