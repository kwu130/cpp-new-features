# Modules

Modules 用显式导入关系替代文本式头文件包含，可减少宏泄漏和重复解析。模块构建流程尚受编译器与构建系统实现差异影响。

模块接口单元：

<!-- example id="cpp20-modules" std="c++20" file="math.cppm" kind="modules" compilers="gcc" output="42" -->
```cpp
export module math;

export int add(int left, int right) {
    return left + right;
}
```

导入模块的程序：

<!-- example id="cpp20-modules" std="c++20" file="main.cpp" kind="modules" compilers="gcc" output="42" -->
```cpp
import math;

#include <iostream>

int main() {
    std::cout << add(20, 22) << '\n';
}
```

验证器在 GCC 任务中先以 `-fmodules-ts` 构建接口单元和 BMI，再编译、链接并运行调用程序。Apple Clang 与 GCC 的模块产物和命令行并不兼容，因此本例明确由 GCC CI 验证。

模块边界应围绕稳定接口设计；不要机械地把每个旧头文件一对一转换为模块。

## Modules 解决的根本问题

头文件通过预处理器文本包含，每个翻译单元重复解析同一声明，宏和包含顺序会影响含义。Modules 把接口作为编译后的语义实体导入，宏默认不跨模块边界传播，声明只在显式 `export` 后对导入方可见。

模块不是包管理器，也不决定源文件目录、依赖下载或二进制发布格式。BMI/CMI 通常与编译器版本、选项和目标平台紧密耦合，不适合作为长期通用二进制接口文件分发。

## 单元与分区

主模块接口单元以 `export module name;` 声明并导出接口。模块实现单元使用 `module name;`，能访问模块内部声明但不重新导出。大型模块可拆成分区，并选择哪些分区由主接口重新导出。

全局模块片段允许在模块声明前包含传统头文件，私有模块片段可把实现限制在接口单元后部。迁移时必须区分文本头文件、header unit 和命名模块，它们的宏可见性不同。

## 构建图与 BMI

编译器必须先处理被导入模块的接口并生成 BMI，再编译导入者，因此构建系统需要扫描 import 依赖并按拓扑顺序调度。与头文件依赖只靠时间戳不同，Modules 需要理解编译命令、模块名到源文件/BMI 的映射。

示例验证器先编译 `math.cppm`，生成 GCC 模块缓存和对象文件，然后编译导入者并链接。Clang、GCC、MSVC 的命令、扩展名和缓存管理不同，这也是必须由构建系统封装的原因。

## 可见性、链接与 ODR

未导出声明可供同一模块的实现单元使用，却不会进入导入方名称查找。导出并不等同于动态库符号导出；共享库可见性和 ABI 仍需平台属性与构建配置。

模块能减少因重复文本定义产生的 ODR 风险，但同一程序混用头文件声明与模块声明仍可能制造实体归属问题。迁移必须从依赖图和第三方兼容性出发逐步进行。

## 工程迁移策略

先选择宏依赖少、接口稳定的叶子库试点；确保构建系统原生支持依赖扫描；固定编译器工具链与缓存失效策略；测量干净构建和增量构建；保留非模块消费者需要的兼容入口，避免一次性转换整个代码库。

## 权威资料

- [P1103R3：Modules](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p1103r3.pdf)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
