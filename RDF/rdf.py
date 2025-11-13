#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON三元组转RDF脚本
将JSON文件中的三元组数据转换为基于IRI标准的RDF格式
"""

import json
import urllib.parse
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD
import argparse
import os
import sys

class TriplesToRDF:
    def __init__(self, base_uri="http://V1.SciMKG.AAAI2026/"):
        """
        初始化RDF转换器
        
        Args:
            base_uri (str): 基础URI，用于生成IRI
        """
        self.graph = Graph()
        self.base_uri = base_uri.rstrip('/') + '/'  # 确保以斜杠结尾
        
        # 定义命名空间
        self.EDUKG = Namespace(self.base_uri)
        self.graph.bind("edukg", self.EDUKG)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        
        # 定义属性映射
        self.predicate_mapping = {
            "has an explanation": "hasExplanation",
            "is an explanationof": "isExplanationOf",
            "has an audio": "hasAudio",
            "is an audio of": "isAudioOf",
            "is an image of": "isImageOf",
            "has an image": "hasImage",
            "has a video": "hasVideo",
            "is a video of": "isVideoOf",
            "related to": "related to",
            "is an exercise of": "isExerciseOf",
            "has an exercise": "hasExercise",
            # 可以根据需要添加更多映射
        }
        
        # 定义实体类型和颜色映射
        self.entity_types = {
            "concept": {"class": self.EDUKG.Concept, "color": "#3498db"},        # 蓝色
            "explanation": {"class": self.EDUKG.Explanation, "color": "#e74c3c"}, # 红色
            "audio": {"class": self.EDUKG.Audio, "color": "#f39c12"},           # 橙色
            "image": {"class": self.EDUKG.Image, "color": "#2ecc71"},           # 绿色
            "video": {"class": self.EDUKG.Video, "color": "#9b59b6"},           # 紫色
            "knowledgepoint": {"class": self.EDUKG.Knowledgepoint, "color": "#1abc9c"}, # 青色
            "exercise": {"class": self.EDUKG.Exercise, "color": "#e67e22"}      # 深橙色
        }
        
        # 谓语到主语实体类型的映射
        self.predicate_to_subject_type = {
            "has an explanation": "concept",
            "has an audio": "concept", 
            "has an image": "concept",
            "has an video": "concept",
            "is an explanationof": "explanation",
            "is an audio of": "audio",
            "is an image of": "image", 
            "is an video of": "video",
            "has an exercise": "knowledgepoint",
            "is an exercise of": "exercise",
            "related to": "concept" 
        }
        
        # 谓语到宾语实体类型的映射（当宾语不是字面量时）
        self.predicate_to_object_type = {
            "has an explanation": "explanation",
            "has an audio": "audio", 
            "has an image": "image",
            "has an video": "video",
            "is an explanationof": "concept",
            "is an audio of": "concept",
            "is an image of": "concept", 
            "is an video of": "concept",
            "has an exercise": "exercise",
            "is an exercise of": "knowledgepoint",
            "related to": "knowledgepoint" 
        }
        
        # 初始化实体类型定义
        self._initialize_entity_types()
    
    def _initialize_entity_types(self):
        """初始化实体类型的RDF定义"""
        for type_name, type_info in self.entity_types.items():
            # 为每个实体类型添加颜色属性
            self.graph.add((type_info["class"], self.EDUKG.hasColor, Literal(type_info["color"])))
            self.graph.add((type_info["class"], RDF.type, RDFS.Class))
    
    def normalize_input(self, value):
        """
        标准化输入值，确保返回字符串
        
        Args:
            value: 输入值（可能是字符串、整数、浮点数等）
            
        Returns:
            str: 标准化后的字符串
        """
        if value is None:
            return ""
        
        # 转换为字符串
        str_value = str(value)
        
        # 清理文本：移除换行符和多余空格
        cleaned_value = str_value.strip().replace('\n', '').replace('\r', '')
        
        return cleaned_value
    
    def create_iri(self, text):
        """
        从文本创建IRI
        
        Args:
            text: 原始文本（可能是字符串或其他类型）
            
        Returns:
            URIRef: 生成的IRI
        """
        # 先标准化输入
        cleaned_text = self.normalize_input(text)
        
        # 如果清理后为空，使用默认值
        if not cleaned_text:
            cleaned_text = "unknown"
        
        # URL编码特殊字符
        encoded_text = urllib.parse.quote(cleaned_text, safe='')
        
        # 创建完整的IRI
        iri = URIRef(self.base_uri + encoded_text)
        return iri
    
    def create_predicate_iri(self, predicate):
        """
        为谓语创建IRI
        
        Args:
            predicate: 谓语文本（可能是字符串或其他类型）
            
        Returns:
            URIRef: 谓语IRI
        """
        # 先标准化输入
        predicate_str = self.normalize_input(predicate)
        
        # 使用映射表或直接转换
        mapped_predicate = self.predicate_mapping.get(predicate_str, predicate_str)
        
        # 清理和编码
        cleaned_predicate = mapped_predicate.replace(' ', '_')
        encoded_predicate = urllib.parse.quote(cleaned_predicate, safe='')
        
        return URIRef(self.base_uri + "property/" + encoded_predicate)
    
    def determine_object_type(self, predicate_text, object_value):
        """
        确定宾语的数据类型
        
        Args:
            predicate_text (str): 谓语文本
            object_value: 宾语值
            
        Returns:
            tuple: (is_literal, datatype_or_lang)
        """
        predicate_str = self.normalize_input(predicate_text)
        
        # 解释性文本使用中文字面量
        if predicate_str in ["has an explanation"]:
            return True, "zh"
        
        # 数字类型
        if isinstance(object_value, (int, float)):
            if isinstance(object_value, int):
                return True, XSD.integer
            else:
                return True, XSD.decimal
        
        # 检查字符串是否为数字
        if isinstance(object_value, str):
            try:
                int(object_value)
                return True, XSD.integer
            except ValueError:
                try:
                    float(object_value)
                    return True, XSD.decimal
                except ValueError:
                    pass
        
        # 默认情况：作为IRI处理
        return False, None
    
    def add_entity_type(self, entity_iri, entity_type):
        """
        为实体添加类型信息
        
        Args:
            entity_iri: 实体IRI
            entity_type: 实体类型字符串
        """
        if entity_type in self.entity_types:
            entity_class = self.entity_types[entity_type]["class"]
            self.graph.add((entity_iri, RDF.type, entity_class))
    
    def add_triple_to_graph(self, subject_text, predicate_text, object_text):
        """
        将三元组添加到RDF图中
        
        Args:
            subject_text: 主语文本（可能是字符串或其他类型）
            predicate_text: 谓语文本（可能是字符串或其他类型）
            object_text: 宾语文本（可能是字符串或其他类型）
        """
        # 创建主语IRI
        subject_iri = self.create_iri(subject_text)
        
        # 创建谓语IRI
        predicate_iri = self.create_predicate_iri(predicate_text)
        
        # 标准化谓语文本用于映射
        predicate_str = self.normalize_input(predicate_text)
        
        # 确定宾语类型
        is_literal, datatype_or_lang = self.determine_object_type(predicate_text, object_text)
        
        if is_literal:
            # 创建字面量
            if isinstance(datatype_or_lang, str) and datatype_or_lang == "zh":
                # 中文字面量
                object_literal = Literal(self.normalize_input(object_text), lang="zh")
            else:
                # 类型化字面量
                object_literal = Literal(object_text, datatype=datatype_or_lang)
            
            self.graph.add((subject_iri, predicate_iri, object_literal))
        else:
            # 创建宾语IRI
            object_iri = self.create_iri(object_text)
            self.graph.add((subject_iri, predicate_iri, object_iri))
            
            # 为宾语添加类型信息（当宾语不是字面量时）
            object_type = self.predicate_to_object_type.get(predicate_str)
            if object_type:
                self.add_entity_type(object_iri, object_type)
        
        # 根据谓语为主语添加适当的类型信息
        subject_type = self.predicate_to_subject_type.get(predicate_str, "concept")
        self.add_entity_type(subject_iri, subject_type)
    
    def load_json_triples(self, json_file_path):
        """
        从JSON文件加载三元组
        
        Args:
            json_file_path (str): JSON文件路径
            
        Returns:
            list: 三元组列表
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                triples = json.load(f)
            
            print(f"成功加载 {len(triples)} 个三元组")
            return triples
            
        except FileNotFoundError:
            print(f"错误：找不到文件 {json_file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"错误：JSON解析失败 - {e}")
            return []
        except Exception as e:
            print(f"错误：加载文件时出现问题 - {e}")
            return []
    
    def convert_triples_to_rdf(self, triples):
        """
        将三元组列表转换为RDF
        
        Args:
            triples (list): 三元组列表
        """
        print("开始转换三元组为RDF...")
        
        error_count = 0
        for i, triple in enumerate(triples):
            if len(triple) != 3:
                print(f"警告：跳过格式不正确的三元组 #{i}: {triple}")
                error_count += 1
                continue
            
            subject, predicate, obj = triple
            
            try:
                self.add_triple_to_graph(subject, predicate, obj)
            except Exception as e:
                print(f"警告：处理三元组 #{i} 时出错: {e}")
                print(f"  三元组内容: {triple}")
                print(f"  数据类型: {type(subject)}, {type(predicate)}, {type(obj)}")
                error_count += 1
                continue
            
            # 显示进度
            if (i + 1) % 10000 == 0:
                print(f"已处理 {i + 1} 个三元组...")
        
        success_count = len(triples) - error_count
        print(f"转换完成！共处理 {len(triples)} 个三元组")
        print(f"成功转换: {success_count} 个，跳过错误: {error_count} 个")
        print(f"RDF图包含 {len(self.graph)} 个语句")
    
    def save_rdf(self, output_file, format='turtle'):
        """
        保存RDF图到文件
        
        Args:
            output_file (str): 输出文件路径
            format (str): RDF格式 ('turtle', 'xml', 'n3', 'nt')
        """
        try:
            self.graph.serialize(destination=output_file, format=format)
            print(f"RDF文件已保存到: {output_file}")
        except Exception as e:
            print(f"错误：保存RDF文件失败 - {e}")
    
    def print_sample(self, num_triples=5):
        """
        打印样例RDF三元组
        
        Args:
            num_triples (int): 要打印的三元组数量
        """
        print(f"\n样例RDF三元组 (前{num_triples}个):")
        print("-" * 50)
        
        count = 0
        for subject, predicate, obj in self.graph:
            if count >= num_triples:
                break
            print(f"主语: {subject}")
            print(f"谓语: {predicate}")
            print(f"宾语: {obj}")
            print("-" * 30)
            count += 1
    
    def analyze_data_types(self, triples, sample_size=1000):
        """
        分析数据类型分布
        
        Args:
            triples (list): 三元组列表
            sample_size (int): 分析的样本大小
        """
        print("\n=== 数据类型分析 ===")
        
        type_stats = {
            'subject_types': {},
            'predicate_types': {},
            'object_types': {}
        }
        
        sample_triples = triples[:sample_size] if len(triples) > sample_size else triples
        
        for triple in sample_triples:
            if len(triple) == 3:
                subject, predicate, obj = triple
                
                # 统计类型
                type_stats['subject_types'][type(subject).__name__] = type_stats['subject_types'].get(type(subject).__name__, 0) + 1
                type_stats['predicate_types'][type(predicate).__name__] = type_stats['predicate_types'].get(type(predicate).__name__, 0) + 1
                type_stats['object_types'][type(obj).__name__] = type_stats['object_types'].get(type(obj).__name__, 0) + 1
        
        for category, stats in type_stats.items():
            print(f"\n{category}:")
            for data_type, count in stats.items():
                print(f"  {data_type}: {count}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='将JSON三元组转换为RDF格式')
    parser.add_argument('--input', '-i', default=r'Triples.json', 
                       help='输入JSON文件路径 (默认: Triples.json)')
    parser.add_argument('--output', '-o', default=r'SciMKG.ttl', 
                       help='输出RDF文件路径 (默认: output.ttl)')
    parser.add_argument('--format', '-f', default='turtle', 
                       choices=['turtle', 'xml', 'n3', 'nt'],
                       help='RDF输出格式 (默认: turtle)')
    parser.add_argument('--base-uri', '-b', default='http://V1.SciMKG.AAAI2026/',
                       help='基础URI (默认: http://V1.SciMKG.AAAI2026/)')
    parser.add_argument('--sample', '-s', action='store_true',
                       help='显示转换后的样例三元组')
    parser.add_argument('--analyze', '-a', action='store_true',
                       help='分析数据类型分布')
    
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    if not os.path.exists(args.input):
        print(f"错误：输入文件 '{args.input}' 不存在")
        sys.exit(1)
    
    print("=== JSON三元组转RDF工具 ===")
    print(f"输入文件: {args.input}")
    print(f"输出文件: {args.output}")
    print(f"输出格式: {args.format}")
    print(f"基础URI: {args.base_uri}")
    print()
    
    # 创建转换器
    converter = TriplesToRDF(base_uri=args.base_uri)
    
    # 加载JSON三元组
    triples = converter.load_json_triples(args.input)
    if not triples:
        print("没有找到有效的三元组数据")
        sys.exit(1)
    
    # 分析数据类型（如果要求）
    if args.analyze:
        converter.analyze_data_types(triples)
    
    # 转换为RDF
    converter.convert_triples_to_rdf(triples)
    
    # 保存RDF文件
    converter.save_rdf(args.output, args.format)
    
    # 显示样例（如果要求）
    if args.sample:
        converter.print_sample()
    
    print("\n转换完成！")

if __name__ == "__main__":
    main()