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
from concurrent.futures import ProcessPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, BarColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
import multiprocessing
import binascii
import struct
import base64
import json
import os
import threading
import time
from Crypto.Cipher import AES

console = Console()

# 全局锁用于文件写入
file_lock = threading.Lock()

def decrypt_chunk(chunk, key_box, start_offset):
    """优化的块解密函数"""
    chunk_length = len(chunk)
    decrypted = bytearray(chunk_length)
    
    for i in range(chunk_length):
        j = (start_offset + i + 1) & 0xff
        decrypted[i] = chunk[i] ^ key_box[(key_box[j] + key_box[(key_box[j] + j) & 0xff]) & 0xff]
    
    return decrypted

def dump(file_path, name, progress_callback=None):
    """优化的解密函数"""
    core_key = binascii.a2b_hex("687A4852416D736F356B496E62617857")
    meta_key = binascii.a2b_hex("2331346C6A6B5F215C5D2630553C2728")
    unpad = lambda s: s[0:-(s[-1] if type(s[-1]) == int else ord(s[-1]))]
    
    try:
        start_time = time.time()
        with open(file_path, 'rb') as f:
            # 验证文件头
            header = f.read(8)
            assert binascii.b2a_hex(header) == b'4354454e4644414d'
            f.seek(2, 1)
            
            # 读取并解密密钥
            key_length = struct.unpack('<I', f.read(4))[0]
            key_data = bytearray(f.read(key_length))
            for i in range(len(key_data)):
                key_data[i] ^= 0x64
            
            cryptor = AES.new(core_key, AES.MODE_ECB)
            key_data = unpad(cryptor.decrypt(key_data))[17:]
            
            # 生成密钥盒
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
            
            # 读取元数据
            meta_length = struct.unpack('<I', f.read(4))[0]
            meta_data = bytearray(f.read(meta_length))
            for i in range(len(meta_data)):
                meta_data[i] ^= 0x63
            
            meta_data = base64.b64decode(meta_data[22:])
            cryptor = AES.new(meta_key, AES.MODE_ECB)
            meta_data = json.loads(unpad(cryptor.decrypt(meta_data)).decode('utf-8')[6:])
            
            # 跳过CRC32和封面数据
            f.seek(4, 1)  # CRC32
            f.seek(5, 1)  # gap
            image_size = struct.unpack('<I', f.read(4))[0]
            f.seek(image_size, 1)  # 跳过封面数据
            
            # 准备输出文件
            file_name = os.path.splitext(os.path.basename(file_path))[0] + '.' + meta_data['format']
            output_path = os.path.join("02_decrypted", file_name)
            
            # 获取音频数据大小
            audio_start = f.tell()
            f.seek(0, 2)  # 移到文件末尾
            total_size = f.tell() - audio_start
            f.seek(audio_start)  # 回到音频数据开始位置
            
            # 使用更大的缓冲区进行解密
            BUFFER_SIZE = 0x40000  # 256KB 缓冲区
            
            with open(output_path, 'wb') as output_file:
                processed = 0
                
                while processed < total_size:
                    chunk = f.read(min(BUFFER_SIZE, total_size - processed))
                    if not chunk:
                        break
                    
                    # 解密数据块
                    decrypted_chunk = decrypt_chunk(chunk, key_box, processed)
                    output_file.write(decrypted_chunk)
                    processed += len(chunk)
                    
                    # 回调进度更新
                    if progress_callback:
                        progress_callback(len(chunk))
        
        elapsed = time.time() - start_time
        speed = total_size / (1024 * 1024) / elapsed if elapsed > 0 else 0
        
        # 线程安全地写入已处理文件列表
        with file_lock:
            with open('cracked.txt', 'a', encoding='utf-8') as f:
                f.write(name + '\n')
        
        return file_name, speed, total_size
        
    except Exception as e:
        return None, 0, 0

def process_file_wrapper(args):
    """多进程包装函数"""
    file_path, name = args
    return dump(file_path, name)

def main():
    """主函数，实现并行处理"""
    console.print(Panel.fit("🚀 NCM 并行解密器", style="bold blue"))
    console.print("✨ 优化技术：多进程并行 + 大缓冲区 + 优化算法")
    console.print("📁 使用规范化目录结构：01_original -> 02_decrypted\n")
    
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
            files_to_process.append((file, name))
    
    if not files_to_process:
        console.print("❌ 在 01_original/ 目录中没有找到需要处理的 .ncm 文件", style="red")
        console.print("💡 提示：请将NCM文件放入 01_original/ 目录", style="yellow")
        return
    
    total_size = sum(fp.stat().st_size for fp, _ in files_to_process)
    max_workers = min(multiprocessing.cpu_count(), len(files_to_process), 4)
    
    console.print(f"📁 找到 [bold cyan]{len(files_to_process)}[/bold cyan] 个文件需要处理")
    console.print(f"💾 总大小: [bold yellow]{total_size/(1024*1024):.1f} MB[/bold yellow]")
    console.print(f"⚡ 使用 [bold green]{max_workers}[/bold green] 个并行进程")
    console.print(f"📂 输出目录: [bold blue]02_decrypted/[/bold blue]\n")
    
    # 创建结果统计表
    results_table = Table(title="🎵 解密结果统计")
    results_table.add_column("文件名", style="cyan", width=25)
    results_table.add_column("大小", justify="right", style="yellow")
    results_table.add_column("速度", justify="right", style="green")
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
        
        main_task = progress.add_task("🔓 总体进度", total=len(files_to_process))
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(process_file_wrapper, file_info): file_info 
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
                        
                        # 添加到结果表
                        results_table.add_row(
                            file_name[:23] + "..." if len(file_name) > 25 else file_name,
                            f"{file_size/(1024*1024):.1f} MB",
                            f"{speed:.1f} MB/s",
                            "✅ 成功"
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
    
    # 显示总结信息
    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("", style="bold")
    summary_table.add_column("", style="")
    
    summary_table.add_row("🎉 处理完成", "")
    summary_table.add_row("✅ 成功", f"[bold green]{successful}[/bold green] 个文件")
    summary_table.add_row("❌ 失败", f"[bold red]{failed}[/bold red] 个文件")
    summary_table.add_row("⏱️  总耗时", f"[bold yellow]{elapsed:.2f}[/bold yellow] 秒")
    summary_table.add_row("🚀 平均速度", f"[bold cyan]{avg_speed:.1f}[/bold cyan] MB/s")
    summary_table.add_row("💾 总处理量", f"[bold magenta]{total_processed_size/(1024*1024):.1f}[/bold magenta] MB")
    
    console.print(Panel(summary_table, title="📊 性能统计", border_style="green"))

if __name__ == '__main__':
    main()