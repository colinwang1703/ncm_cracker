"""
📁 项目目录结构管理器
自动创建和管理文件夹结构
"""

import os
import pathlib
import shutil
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

class ProjectStructure:
    def __init__(self, root_path="."):
        self.root = pathlib.Path(root_path)
        self.folders = {
            "original": self.root / "01_original",
            "decrypted": self.root / "02_decrypted", 
            "compressed": self.root / "03_compressed"
        }
        self.records = {
            "cracked": self.root / "cracked.txt",
            "compressed": self.root / "compressed.txt"
        }
    
    def create_structure(self):
        """创建项目目录结构"""
        console.print(Panel.fit("📁 创建项目目录结构", style="bold blue"))
        
        for name, path in self.folders.items():
            if not path.exists():
                path.mkdir(exist_ok=True)
                console.print(f"✅ 创建目录: {path.name}")
            else:
                console.print(f"📁 目录已存在: {path.name}")
        
        # 确保记录文件存在
        for name, path in self.records.items():
            if not path.exists():
                path.touch()
                console.print(f"📝 创建记录文件: {path.name}")
        
        console.print("\n🎉 项目结构创建完成！")
    
    def organize_existing_files(self):
        """整理现有文件到对应目录"""
        console.print(Panel.fit("🗂️  整理现有文件", style="bold yellow"))
        
        moved_files = {"ncm": 0, "audio": 0, "mp3": 0}
        
        for file in self.root.iterdir():
            if file.is_file():
                # NCM文件 -> 01_original
                if file.suffix.lower() == '.ncm':
                    target = self.folders["original"] / file.name
                    if not target.exists():
                        shutil.move(str(file), str(target))
                        moved_files["ncm"] += 1
                        console.print(f"📦 移动NCM文件: {file.name} -> 01_original/")
                
                # 音频文件 -> 02_decrypted
                elif file.suffix.lower() in ['.flac', '.wav', '.m4a', '.aac', '.ogg']:
                    target = self.folders["decrypted"] / file.name
                    if not target.exists():
                        shutil.move(str(file), str(target))
                        moved_files["audio"] += 1
                        console.print(f"🎵 移动音频文件: {file.name} -> 02_decrypted/")
                
                # MP3文件 -> 03_compressed (如果在result目录外的话)
                elif file.suffix.lower() == '.mp3' and 'result' not in str(file):
                    target = self.folders["compressed"] / file.name
                    if not target.exists():
                        shutil.move(str(file), str(target))
                        moved_files["mp3"] += 1
                        console.print(f"🎧 移动MP3文件: {file.name} -> 03_compressed/")
        
        # 处理result目录中的文件
        result_dir = self.root / "result"
        if result_dir.exists():
            for file in result_dir.iterdir():
                if file.is_file() and file.suffix.lower() == '.mp3':
                    target = self.folders["compressed"] / file.name
                    if not target.exists():
                        shutil.move(str(file), str(target))
                        moved_files["mp3"] += 1
                        console.print(f"🎧 移动MP3文件: {file.name} -> 03_compressed/")
            
            # 删除空的result目录
            try:
                result_dir.rmdir()
                console.print("🗑️  删除空的result目录")
            except OSError:
                console.print("⚠️  result目录不为空，保留")
        
        # 显示统计
        summary_table = Table(show_header=False, box=None)
        summary_table.add_column("", style="bold")
        summary_table.add_column("", style="")
        
        summary_table.add_row("📦 NCM文件", f"{moved_files['ncm']} 个")
        summary_table.add_row("🎵 音频文件", f"{moved_files['audio']} 个") 
        summary_table.add_row("🎧 MP3文件", f"{moved_files['mp3']} 个")
        
        console.print(Panel(summary_table, title="📊 文件整理统计", border_style="green"))
    
    def show_structure(self):
        """显示当前项目结构"""
        console.print(Panel.fit("📁 项目目录结构", style="bold cyan"))
        
        structure_table = Table(show_header=False, box=None)
        structure_table.add_column("", style="bold")
        structure_table.add_column("", style="")
        structure_table.add_column("", style="dim")
        
        for name, path in self.folders.items():
            if path.exists():
                file_count = len([f for f in path.iterdir() if f.is_file()])
                size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                size_mb = size / (1024 * 1024)
                
                if name == "original":
                    structure_table.add_row("📦 01_original/", f"{file_count} 个文件", f"{size_mb:.1f} MB")
                elif name == "decrypted":
                    structure_table.add_row("🎵 02_decrypted/", f"{file_count} 个文件", f"{size_mb:.1f} MB")
                elif name == "compressed":
                    structure_table.add_row("🎧 03_compressed/", f"{file_count} 个文件", f"{size_mb:.1f} MB")
        
        console.print(structure_table)
        console.print()
        
        # 显示记录文件状态
        for name, path in self.records.items():
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    lines = len([line for line in f.read().strip().split('\n') if line])
                console.print(f"📝 {path.name}: {lines} 条记录")

def main():
    """主函数"""
    console.print(Panel.fit("🗂️  项目结构管理工具", style="bold magenta"))
    
    pm = ProjectStructure()
    
    console.print("1. 创建目录结构")
    console.print("2. 整理现有文件")
    console.print("3. 显示项目结构")
    console.print("4. 全部执行")
    console.print()
    
    choice = input("请选择操作 (1-4): ").strip()
    
    if choice == "1":
        pm.create_structure()
    elif choice == "2":
        pm.organize_existing_files()
    elif choice == "3":
        pm.show_structure()
    elif choice == "4":
        pm.create_structure()
        console.print()
        pm.organize_existing_files()
        console.print()
        pm.show_structure()
    else:
        console.print("❌ 无效选择")

if __name__ == "__main__":
    main()
