# 贡献指南

## 文档约定

- 使用中文解释特性，文件名使用英文 kebab-case。
- 每篇专题依次说明动机、核心语义、完整示例、实践建议、易错点和总结。
- 只介绍对应标准已经具备的能力，不把后续标准的扩展写进早期版本。
- 反面代码或预期编译错误使用 `text` 围栏，不使用 `cpp` 围栏。

## 示例约定

每个 `cpp` 围栏前必须紧邻一行示例元数据：

```text
<!-- example id="unique-id" std="c++17" file="main.cpp" kind="single" compilers="all" output="expected output" -->
```

- `id` 在仓库内唯一；多文件示例通过相同 ID 和不同 `file` 组成一组。
- `std` 只能是 `c++11`、`c++14`、`c++17` 或 `c++20`。
- `compilers="all"` 表示 GCC 与 Clang 都必须通过；工具链敏感示例可以指定 `gcc`。
- `output` 可选；存在时会与删除末尾换行后的标准输出严格比较。
- 示例必须返回 0，并在十秒内结束。

提交前运行：

```shell
python3 tools/verify_examples.py --compiler clang++
python3 tools/verify_examples.py --compiler g++
```

提交信息使用英文 Conventional Commits 风格。

