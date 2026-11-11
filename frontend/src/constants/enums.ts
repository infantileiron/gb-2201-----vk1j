export const states=['active','dormant','completed','lost'] as const;
export const stateLabels=['活跃','休眠','结业','流失'];
export const roleLabels:Record<string,string>={admin:'运营复核人',analyst:'研修分析员',viewer:'课程观察员'};
export const runLabels:Record<string,string>={queued:'排队中',running:'计算中',completed:'已完成',failed:'失败',pending:'待复核',approved:'已通过',rejected:'已退回'};
