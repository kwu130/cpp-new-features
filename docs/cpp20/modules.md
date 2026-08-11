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

