# 致远队
《探究碰撞中的不变量（验证动量守恒定律） --  Python 教具》

## 开发动机
本教具针对高中物理《探究碰撞中的不变量》实验开发。传统实物实验存在现象转瞬即逝、数据读取不便、难以反复演示的问题。因此采用 Python 制作动画仿真教具，直观还原碰撞过程，实时计算并展示动量数据，帮助学生观察规律、验证动量守恒定律，同时丰富课堂数字化教学形式。
## 项目依赖、结构
> 采用 `pygame` 作为主要可视化演示途径。
>
> 使用 `numpy` 处理原始实验模拟数据。
>
> 通过 `matplotlib` `pandas` 导出实验图表
```
.
├── LICENSE               # MIT 协议
├── uv.lock               # 依赖
├── pyproject.toml        # 项目配置
├── momentum_lab          # 项目源文件
│   ├── export            # 数据导出 matplotlib pandas
│   │   ├── __init__.py
│   │   └── chart.py
│   ├── model             # 物理部分 numpy
│   │   ├── __init__.py   
│   │   └── block.py      
│   │── ui                # 可视化交互部分 pygame
│   │   ├── __init__.py
│   │   ├── const.py
│   │   ├── display.py
│   │   ├── surface.py
│   │   └── scene.py
│   ├── __init__.py
│   └── __main__.py       # 入口文件
└── README.MD
```

## 使用
```shell
python -m pip install momentum-lab
momentlab          # 交互实验界面
momentlab --export [--e 0.5] # 仅导出图表 [可选:设定恢复系数]
```

### 物理部分
<!-- 
动量守恒定律：
$$
F_{\text{合外力}} = 0, \quad \sum p_{\text{初态}} = \sum p_{\text{末态}}
$$ -->
`model.block.py`

理想化模型：
+ 物块 `Block`
  + x 物块的坐标(考虑一维正碰)
  + m 物块质量
  + v 物块速度

+ 两体正碰 `D`
  + block_1 物块对象
  + block_2 物块对象
  + e    恢复系数
  + kind 碰撞类型

+ 枚举碰撞类型 `CollisionType`
  + ELASTIC   完全弹性碰撞  
  + PARTIAL   非完全弹性碰撞
  + INELASTIC 完全非弹性碰撞  

### 数据导出部分

`export.chart.py` 绘制图表


### 主要 UI 界面

`ui.scene.py` 模拟交互,面板
辅助文件
+ `ui.const.py`   颜色,布局常数
+ `ui.dispaly.py` 布局工具
+ `ui.surface.py` 显示工具