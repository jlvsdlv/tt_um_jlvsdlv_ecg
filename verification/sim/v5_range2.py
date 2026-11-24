from concurrent.futures import ProcessPoolExecutor
import v5_tran as V5, v4_tran as B, v5_sim as S, json
def job(a):
    tag, amp, cpf0 = a; B.AMP = amp
    if cpf0:
        S.CPF = 1e-18; V5.CT = 0.0
    return B.tran((tag, 2000.0, 0, 1.0, 1e-15))
if __name__ == "__main__":
    with ProcessPoolExecutor(2) as ex:
        for tag, r, err in ex.map(job, [("ideal source 4 mVpp", 4e-3, 0), ("ideal source 4 mVpp, no Cpf/Ct", 4e-3, 1)]):
            print(tag, "FAILED " + err[:300] if r is None else f": gain {r['gain_dB']:.2f} dB THD {r['thd']:.2f}% outCMpp {r['voc_pp_mV']:.1f} mV", flush=True)
