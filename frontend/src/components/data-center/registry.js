// 数据中心 - 前端采集模块注册表
//
// 扩展方式：
// 1. 后端新增 collector（collectors/ 下注册，key 与这里一致）；
// 2. 新建对应的前端模块组件（参考 ZhaopinModule.vue）；
// 3. 在下面映射表中加一行 { key: 组件 }。
// 数据中心页面的模块列表、参数表单均由后端 /api/data-center/modules 元数据驱动，
// 因此除本文件与新组件外，无需改动数据中心页面本身。
import ZhaopinModule from './ZhaopinModule.vue'

export const collectorComponents = {
  zhaopin: ZhaopinModule
}
