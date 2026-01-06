"""
Code removal functionality for dead code elimination.
"""
import ast
import os
from pathlib import Path
from typing import List, Tuple, Dict


class CodeRemover:
    """Handles safe removal of dead code from Python files."""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.backup_dir = self.root_path / '.deadcode_backups'
        self.backup_dir.mkdir(exist_ok=True)
        self.changes_log = []
    
    def backup_file(self, file_path: str) -> str:
        """Create a backup of the file before modification."""
        src_path = Path(file_path)
        backup_path = self.backup_dir / f"{src_path.name}.backup"
        
        # If backup already exists, add timestamp
        if backup_path.exists():
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{src_path.name}.{timestamp}.backup"
        
        with open(src_path, 'r', encoding='utf-8') as src:
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        
        return str(backup_path)
    
    def remove_import(self, file_path: str, import_name: str, line_number: int) -> Dict:
        """Remove a specific import from a file."""
        try:
            # Ensure line_number is an integer
            line_number = int(line_number)
            backup = self.backup_file(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if 0 < line_number <= len(lines):
                removed_line = lines[line_number - 1]
                del lines[line_number - 1]
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                change = {
                    'status': 'success',
                    'file': file_path,
                    'line': line_number,
                    'type': 'import',
                    'removed': removed_line.strip(),
                    'backup': backup
                }
                self.changes_log.append(change)
                return change
            else:
                return {'status': 'error', 'message': 'Invalid line number'}
        
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def remove_function(self, file_path: str, function_name: str, line_number: int) -> Dict:
        """Remove a function definition from a file."""
        try:
            # Ensure line_number is an integer
            line_number = int(line_number)
            backup = self.backup_file(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            lines = content.splitlines(keepends=True)
            
            # Find the function node
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                        start_line = node.lineno - 1
                        end_line = node.end_lineno
                        
                        removed_code = ''.join(lines[start_line:end_line])
                        
                        # Remove the function
                        del lines[start_line:end_line]
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.writelines(lines)
                        
                        change = {
                            'status': 'success',
                            'file': file_path,
                            'line': line_number,
                            'type': 'function',
                            'name': function_name,
                            'removed': removed_code[:200] + '...' if len(removed_code) > 200 else removed_code,
                            'backup': backup
                        }
                        self.changes_log.append(change)
                        return change
            
            return {'status': 'error', 'message': f'Function {function_name} not found'}
        
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def remove_class(self, file_path: str, class_name: str, line_number: int) -> Dict:
        """Remove a class definition from a file."""
        try:
            # Ensure line_number is an integer
            line_number = int(line_number)
            backup = self.backup_file(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            lines = content.splitlines(keepends=True)
            
            # Find the class node
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                        start_line = node.lineno - 1
                        end_line = node.end_lineno
                        
                        removed_code = ''.join(lines[start_line:end_line])
                        
                        # Remove the class
                        del lines[start_line:end_line]
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.writelines(lines)
                        
                        change = {
                            'status': 'success',
                            'file': file_path,
                            'line': line_number,
                            'type': 'class',
                            'name': class_name,
                            'removed': removed_code[:200] + '...' if len(removed_code) > 200 else removed_code,
                            'backup': backup
                        }
                        self.changes_log.append(change)
                        return change
            
            return {'status': 'error', 'message': f'Class {class_name} not found'}
        
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def restore_from_backup(self, backup_path: str) -> Dict:
        """Restore a file from its backup."""
        try:
            backup = Path(backup_path)
            if not backup.exists():
                return {'status': 'error', 'message': 'Backup file not found'}
            
            # Extract original filename from backup
            original_name = backup.name.split('.')[0] + '.py'
            
            # Find the original file in the project
            for file in self.root_path.rglob(original_name):
                with open(backup, 'r', encoding='utf-8') as src:
                    with open(file, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
                
                return {
                    'status': 'success',
                    'message': f'Restored {file} from backup',
                    'file': str(file)
                }
            
            return {'status': 'error', 'message': 'Original file not found'}
        
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_changes_log(self) -> List[Dict]:
        """Get the log of all changes made."""
        return self.changes_log
    
    def clear_changes_log(self):
        """Clear the changes log."""
        self.changes_log = []
